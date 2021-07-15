# @copyright  Copyright (c) 2018-2021 Opscidia

__copyright__ = "Copyright 2021, Opscidia"
__status__ = "development"
__version__ = "0.1.0"


from typing import (
    Union, List, Dict
)

import os, json, logging
from enum import Enum
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.logger import logger as f_logger
from fastapi_mail import FastMail, ConnectionConfig
from configparser import ConfigParser
from uuid import uuid4

from utils.es_utils import get_terms_articles
from corpus import get_corpus
from quantities import main_quantities
from scienceqa import load_sqa, main_sqa
from base import (
    compute_indicators, get_indicators,
    answer_quantities, back_all
)



os.environ["CUDA_VISIBLE_DEVICES"]="-1" 
config = ConfigParser()
config.read("../conf/conf.ini")
PROD = eval(config['MODE']['PRODUCTION'])
INDEX = config['ES']['QUANTITIES']
mail = config['MAIL']
HOST = os.getenv('API_HOST', '0.0.0.0')
PORT = os.getenv('API_PORT', 5000)

uvicorn_logger = logging.getLogger('uvicorn')
f_logger.handlers = uvicorn_logger.handlers
f_logger.setLevel(uvicorn_logger.level)

MAIL = ConnectionConfig(
    MAIL_USERNAME = os.getenv('MAIL_USER', ''),
    MAIL_PASSWORD = os.getenv('MAIL_KEY', ''),
    MAIL_FROM = "noreply@opscidia.com",
    MAIL_FROM_NAME = "Science Checker",
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587)),
    MAIL_SERVER = os.getenv('MAIL_SERVER', ''),
    MAIL_TLS = True,
    MAIL_SSL = False,
    TEMPLATE_FOLDER = mail['TEMPLATE']
)

CLASSIFIER = config['SQA']['CLASSIFIER']
PULLER = config['SQA'].get('PULLER')
EXTRACTOR = config['SQA'].get('EXTRACTOR', 'eqa')

LIST_TASK = list()
DATA_PATH = config['BASE'].get('PATH', '')

##################################################

sampler, classifier, puller = load_sqa(
    CLASSIFIER, PULLER,
    extractor = EXTRACTOR
)

##################################################

class Boolean(Enum):
    TRUE = True
    FALSE = False

class Relation(str, Enum):
    cause = 'cause'
    cure = 'cure'
    increase = 'increase'
    prevent = 'prevent'

class Type(str, Enum):
    values = 'value'
    interval = 'interval'

class Pulling(Enum):
    none = ''
    extractor = EXTRACTOR

class Extraction(Enum):
    rules = 'rules'
    quantities = 'quantities'



app = FastAPI(
    title = "Science Checker",
    version = __version__
)

##################################################

@app.get('/version')
def version():
    return {"version": __version__}


@app.get('/articles',
    summary = "Fetch articles for between two elements"
)
async def fetch_articles(
    first: str, second: str,
    index: str = INDEX,
    ci: bool = Boolean.FALSE,
    ci_terms: str = 'confidence interval,CI',
    source: str = 'DOI,URL,title,authors,abstract,publication_date',
    fields: str = 'abstract',
    limit: int = 10_000
) -> List[Dict]:
    kwargs = locals()
    measure, label = kwargs.pop('first'), kwargs.pop('second').split(',')
    index = kwargs.pop('index')
    kwargs['ci_terms'] = kwargs['ci_terms'].split(',')
    kwargs['source'] = kwargs['source'].split(',')
    kwargs['fields'] = kwargs['fields'].split(',')
    articles = get_terms_articles(measure, label, index, **kwargs)

    return articles


@app.get('/corpus',
    summary = "Get the number of annual publications between two elements",
    tags = ['indicator']
)
async def publications(first:str, second:str) -> List[Dict]:
    """
    - **first**: first element or measure
    - **second**: second element or one label
    """
    index = INDEX
    return get_corpus(**locals())


@app.get('/scienceqa',
    summary = "Boolean Question answering",
    tags = ['indicator']
)
async def boolqa(
    first:str, second:str,
    relation: Relation = Relation.cause,
    pulling: Pulling = Pulling.none,
    limit:int = 100,
    page:int = 1
) -> List[Dict]:

    global puller
    kwargs = locals()
    kwargs['relation'] = kwargs['relation'].value

    results = main_sqa(
        **kwargs,
        index = INDEX,
        sampler = sampler,
        classifier = classifier,
        puller = puller if len(pulling.value) else None
    )

    return results


@app.get('/quantities',
    summary = "Retrieval of significant values",
    tags = ['indicator']
)
async def quantities(
    measure:str, labels:str,
    type: Type = Type.values,
    metric: str = None,
    extraction: Extraction = Extraction.rules
):
    kwargs = locals()
    kwargs['type'] = kwargs['type'].value
    kwargs['extraction'] = kwargs['extraction'].value
    results = main_quantities(**kwargs, index = INDEX)
    return results


@app.post(
    '/indicators/',
    summary = "Create task which compute all indicators",
    tags = ['base']
)
async def compute(
    bg_task: BackgroundTasks,
    first: str,
    second: str,
    relation: Relation = Relation.cause,
    index: str = INDEX,
    pulling: Pulling = Pulling.none,
    extraction: Extraction = Extraction.rules
) -> Dict:

    task_id = str(uuid4())
    LIST_TASK.append(task_id)

    relation = relation.value
    puller_model = puller if len(pulling.value) else None

    bg_task.add_task(
        compute_indicators,
        first, second,
        relation,
        task_id,
        path = DATA_PATH,
        index = index,
        sampler = sampler,
        classifier = classifier,
        puller = puller_model,
        extraction = extraction.value
    )

    return {'id': task_id}



@app.get(
    '/indicators/{task_id}',
    summary = "Get result of task",
    tags = ['base']
)
async def get_task(
    task_id: str
) -> Dict:

    status, data = get_indicators(task_id, LIST_TASK, DATA_PATH)

    if status:
        raise HTTPException(
            status_code = status,
            detail = data['message']
        )
    return data


@app.get(
    '/indicators/',
    summary = "Get Boolean question answering with Quantities field",
    tags = ['base', 'indicator']
)
async def boolean_quantities(
    first:str, second:str,
    relation: Relation = Relation.cause,
    pulling: Pulling = Pulling.none,
    limit:int = 100,
    page:int = 1
) -> List[Dict]:
    """
    The output is the **boolqa**'s output (*scienceqa/*) with the list of quantities for each item.
    """

    global puller
    kwargs = locals()
    kwargs['relation'] = kwargs['relation'].value

    results = answer_quantities(
        **kwargs,
        index = INDEX,
        sampler = sampler,
        classifier = classifier,
        puller = puller if len(pulling.value) else None,
        path = DATA_PATH
    )

    return results


@app.get(
    '/indicators/all/',
    summary = "Get all Boolean question answering with Quantities field",
    tags = ['base', 'indicator']
)
async def ensemble(
    bg_task: BackgroundTasks,
    first:str, second:str,
    relation: Relation = Relation.cause,
    pulling: Pulling = Pulling.none,
    email:str = None
):
    global puller
    kwargs = locals()
    kwargs['relation'] = kwargs['relation'].value

    taskid = f'{first}{second}{relation}'

    bg_task.add_task(
        back_all,
        **kwargs,
        index = INDEX,
        sampler = sampler,
        classifier = classifier,
        puller = puller if len(pulling.value) else None,
        path = DATA_PATH,
        fastmail = FastMail(MAIL),
        logger = f_logger
    )

    return {'id': taskid}


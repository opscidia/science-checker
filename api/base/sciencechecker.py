# @copyright  Copyright (c) 2018-2021 Opscidia

"""
Scienceqa answers a closed-ended question
by extracting relevant information from the articles
"""

__copyright__ = "Copyright 2021, Opscidia"
__status__ = "development"
__all__ = [
    'compute_indicators',
    'get_indicators',
    'answer_quantities',
    'back_all'
]

import pandas as pd
import json
import time
from datetime import datetime
from collections import Counter
from glob import glob
from typing import List, Tuple, Dict
from pprint import pprint as cat

from fastapi_mail import FastMail, MessageSchema

from scienceqa import instanciate, predict_sqa, main_sqa
from quantities import main_quantities, preprocessing, regather



def compute_indicators(
    first: str,
    second: str,
    relation: str,
    task_id: str,
    **kwargs
) -> None:
    """
    Compute all indicators
    
    first: str.
    second: str.
    relation: str. One of cause, increase, prevent, cure.
    task_id: str. Used for output json.
    path: str. Optional. Folder path to save json. Default to ''
    logger: Logger. Optional.
    **kwargs: quantities and scienceqa predict kwargs
    
    :return: None
    """
    
    path = kwargs.get('path', '')
    index = kwargs.pop('index')
    sampler = kwargs.pop('sampler')
    classifier = kwargs.pop('classifier')
    puller = kwargs.get('puller')
    extraction = kwargs.get('extraction')
    logger = kwargs.get('logger')
    
    articles = instanciate(first, second, relation, index)
    start = time.time()
    
    try:
        indic_1 = dict(sorted(Counter(
                map(lambda x: x['publication_date'][:4],
                            articles.to_dict('records'))).items()))
    except Exception as e:
        indic_1 = None
        message = f"Task: {task_id} - {str(e)}"
        if logger: logger.error(message)
        else: print("[ERROR] " + message)
    time_1 = time.time()
    
    try:
        indic_2 = predict_sqa(articles, sampler, classifier, puller)
    except Exception as e:
        indic_2 = articles
        message = f"Task: {task_id} - {str(e)}"
        if logger: logger.error(message)
        else: print("[ERROR] " + message)
    time_2 = time.time()
    
    try:
        indic_3 = (
            pd.
            DataFrame(main_quantities(measure = first, labels = second, index = index, extraction = extraction))
            .set_index('id')
            [['text', 'quantityLeast', 'quantityMost', 'unit', 'label']])

        indic_3 = indic_3.where(indic_3.notnull(), None)
        indic_3 = [{'_id':k, 'quantities':g.to_dict(orient='records')} for k, g in indic_3.groupby(level = 0)]
    except Exception as e:
        indic_3 = [{'_id': None, 'quantities': None}]
        message = f"Task: {task_id} - {str(e)}"
        if logger: logger.error(message)
        else: print("[ERROR] " + message)
    time_3 = time.time()
    
    indic_0 = pd.merge(
        pd.concat([pd.DataFrame(indic_2), articles[['publication_date']]], axis=1),
        pd.DataFrame(indic_3),
        on = '_id',
        how = 'left')
    indic_0 = indic_0.where(indic_0.notnull(), None).to_dict('records')
    
    results = {
        'corpus': indic_1,
        'articles': indic_0
    }
    
    with open(f"{path}{task_id}.json", "w") as outfile:  
        json.dump(results, outfile)
    
    times = list(map(lambda x:round(x-start, 3), (time_1, time_2, time_3)))
    message = "Done: {} - 1: {}s; 2: {}s; 3: {}s".format(task_id, *times)
    if logger: logger.info(message)
    else: print("[INFO] " + message)



def get_indicators(
    task_id: str,
    task_list: List[str],
    path: str = ''
) -> Tuple[int, dict]:
    """
    Get computing result
    task_id: str.
    task_list: [str, ]. List of task id
    path: str. Folder path of results.
    
    :return: status code, dict of result or message
    """
    
    if task_id not in task_list:
        status = 404
        data = {'message': 'This task not in queue'}
    else:
        try:
            status = 0
            with open(f"{path}{task_id}.json") as infile:
                data = json.load(infile)
        except:
            status = 202
            data = {'message': f'Task {task_id} not finished yet'}
    
    return status, data


def answer_quantities(
    first: str,
    second: str,
    relation: str,
    **kwargs
) -> List[Dict]:
    """
    Response for Answer and Quantities indicator

    first: str.
    second: str.
    relation: str. One of cause, increase, prevent, cure.
    **kwargs: quantities and scienceqa predict kwargs
    
    :return: List of dict. main_sqa output w/ quantities field
    """

    path = kwargs.get('path', '')
    
    if glob(f"{path}{first}{second}{relation}.json"):
        response = pd.read_json(f"{path}{first}{second}{relation}.json")
        return response.to_dict('records')


    response = main_sqa(first = first, second = second, relation = relation, **kwargs)

    if len(response):
        articles = preprocessing(
            pd.DataFrame(response)
            .rename(columns = {"_id": "id", "response": "abstract"})
        )
        quantities = regather(articles, [first, second])
        quantities = (
            quantities
            .where(quantities.notnull(), None)
            .rename(columns = {"id": "_id"})
            [['_id', 'text', 'unit', 'label', 'quantityLeast', 'quantityMost']]
        )
        quantities = {_id: table.to_dict('records') for _id, table in quantities.groupby('_id')}
        
        for article in response:
            article['quantities'] = quantities.get(article['_id'], [])
        
        return response


async def back_all(
    first: str,
    second: str,
    relation: str,
    email: str = None,
    **kwargs
) -> None:

    path = kwargs.get('path', '')
    logger = kwargs.get('logger')
    fastmail = kwargs['fastmail']
    date = datetime.now().strftime("%d %B, %Y at %H:%M:%S")

    if glob(f"{path}{first}{second}{relation}.json"):
        message = "Done: {} {} {} - Already exist".format(first, relation, second)
        if logger: logger.info(message)
        else: print("[INFO] " + message)

        if not email: return None

        message = MessageSchema(
            subject = "Science does not wait",
            recipients = [email],
            subtype = "html",
            body = {
                'first': first,
                'second': second,
                'relation': relation,
                'size': 1,
                'date': date,
                'year': datetime.now().strftime("%Y"),
                'user': email.split('@')[0]
            }
        )
        
        await fastmail.send_message(message, template_name = "email_template.html")
        return None

    start = time.time()
    response = answer_quantities(first = first, second = second, relation = relation, limit = 10_000, **kwargs)
    end = round(time.time() - start, 3)
    
    with open(f"{path}{first}{second}{relation}.json", "w") as outfile:  
        json.dump(response, outfile)
    
    if not email: return None

    message = MessageSchema(
        subject = "Science does not wait | Science Checker",
        recipients = [email],
        subtype = "html",
        body = {
            'first': first,
            'second': second,
            'relation': relation,
            'size': len(response),
            'date': date,
            'year': datetime.now().strftime("%Y"),
            'user': email.split('@')[0]
        }
    )
    
    await fastmail.send_message(message, template_name = "email_template.html")
    
    message = "Done: {} {} {} - {}".format(first, relation, second, end)
    if logger: logger.info(message)
    else: print("[INFO] " + message)
    
    
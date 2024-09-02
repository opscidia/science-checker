# NOTE: Do not open this file in Open Source Project
# bc it contains Opscidia's private information.

import re, os
import numpy as np
import pandas as pd
from datetime import datetime
from elasticsearch_dsl import Q
from itertools import product, chain
from nltk.corpus import wordnet
from elasticsearch import AsyncElasticsearch, Elasticsearch
from elasticsearch_dsl import search as sch, Q
from requests import packages
from typing import List, Optional, Dict, Any, Union
from shlex import split

packages.urllib3.disable_warnings()




SOURCES = [
    "title", "abstract", "authors", "DOI", "URLs",
    # Add here the fields you want to retrieve from your index
]



def search_articles(keywords: str, pipeline):
    """
    Search articles to answer questions
    """
    while True:
        try:
            aug_keywords, verbs, k_entities, b_entities, cumulated = augment_query(
                keywords = keywords,
                pipeline = pipeline
            )
            break
        except: continue
    
    cumulated = re.sub(r'\?', '', cumulated).strip()
    kwargs = query_generator(verbs, k_entities, b_entities, cumulated)
    
    results = articles_results(keywords, aug_keywords, kwargs)
    return results




def get_article_by_id(
    id: str,
):
    """
    Get article by id
    :param id: str
    """
    connection = es_connection()
    kwargs = {"source": SOURCES}
    results = connection.search(
        **search_ids_query([id, ], **kwargs)
    )
    count = results.hits.total.value
    if count == 0:
        return None

    df = pd.DataFrame(map(lambda x: x.to_dict(), results.hits.hits))
    df = (
        pd.concat([df, pd.json_normalize(df._source)], axis=1)
        .drop(columns=['_source', '_index'])
        .where(lambda x: x.notna(), None)
    )

    return df.to_dict('records')[0]




def augment_query( keywords: str, pipeline):
    """
    Augment query with synonyms and hypernyms.
    :param query: The query to augment.
    :param pipeline: The spaCy pipeline for query augmentation.
    """
    if keywords.strip()[-1] != "?": keywords += "?"
    
    doc = pipeline(keywords)
    entities = {
        ent.text: [
            ent._.normal_term,
            ent._.description and re.findall(r"\[\[(.*?)\]\]", ent._.description)[0] or None,
        ] for ent in doc.ents
    }
    verbs = {
        ent.text: list({
            l.lemmas()[0].name() for l in wordnet.synsets(ent.text)
        }) for ent in doc if ent.pos_ == "VERB"
    }

    augmented, aug_entities, aug_keywords = [], [], []
    for i, token in enumerate(doc):
        if token.ent_type_:
            if token.ent_iob == 1: continue
            k_type = token.ent_type_
            entity = token.text
            chunk = token
            while chunk.nbor().ent_iob == 1:
                chunk = chunk.nbor()
                entity = entity + " " + chunk.text
            keywords = {
                entity,
                *list(filter(
                    bool,
                    entities.get(entity, [None, None])
                ))
            }
        elif token.pos_ == "VERB":
            k_type = "VERB"
            keywords = {
                token.text,
                *list(filter(
                    bool,
                    verbs.get(token.text, [None])
                ))
            }
        else: keywords, k_type = {token.text,}, None
        augmented.append(list(keywords))
        aug_entities.append(list(keywords) if token.ent_type_ else [token.text,])
        aug_keywords.append(dict(keyword=list(keywords), type=k_type))

    cumulated = ' '.join(chain(*augmented))
    b_entities = list(set(map(lambda x: " ".join(x).lower(), product(*aug_entities))))

    k_entities = []
    for keyword, syns in entities.items():
        k_entity = [keyword.lower(),]
        for syn in syns:
            if not syn: continue
            if syn.lower() not in k_entity:
                k_entity.append(syn.lower())
        k_entities.append(k_entity)
    return aug_keywords,verbs ,k_entities, b_entities,cumulated




def query_generator(
    verbs,
    k_entities,
    b_entities,
    cumulated
):
    """
    Generate query for Elasticsearch
    """
    # Based on your data structure, you should adapt this function to fit your needs.
    # Here, we are using a simple query with should and must clauses
    # using only some of the augmented keywords


    cumulated = re.sub(r'\?', '', cumulated).strip()
    should = [
        Q(
            'multi_match',
            query=query,
            type='phrase',
            fields=['title', 'abstract', 'authors'],
            slop=2,
            boost=2
        ) for query in b_entities
    ]
    # Based on your data, you can add more should queries here to boost some specific entities
    
    
    must = [
        Q(
            'multi_match',
            query=cumulated,
            operator='or',
            type='cross_fields',
            minimum_should_match='1<50%',
            fields=['title', 'abstract', 'authors'],
            boost=1
        )
    ]
    # Based on your data, you can add more must queries here to boost some specific entities
    
    filters = [Q('exists', field='abstract')] 

    query = Q(
        'bool',
        must = must,
        filter = filters,
        should = should,
        minimum_should_match = 1,
    )

    highl = Q(
        'multi_match',
        operator = 'or',
        query = cumulated,
        type = 'cross_fields',
        analyzer = 'whitespace_wdg',
        minimum_should_match = 0,
        fields = ['title', 'abstract']
    )

    highlight = {
        "highlight_query": highl.to_dict(),
        "order": "score",
        "type": "unified",
        "boundary_scanner": "sentence",
        "boundary_scanner_locale": "en-US",
        "pre_tags": ["<span class='hglt'>"],
        "post_tags": ["</span>"],
        "fields": {
            "title": {
                "number_of_fragments": 0
            },
            "abstract": {
                "number_of_fragments": 4,
                "fragment_size": 100,
                "phrase_limit": 10
            }
        }
    }

    return {
        "query": query.to_dict(),
        "highlight": highlight,
        "sources": SOURCES,
        "extras": {
            'from': 0,
            'size': 10,
            'track_total_hits': True,
        }
    }




def articles_results(
    keywords,
    aug_keywords,
    kwargs,
):
    """
    Search articles in Elasticsearch and return results
    """

    connection = es_connection()

    results = connection.search(**kwargs)
    count = results.hits.total.value

    df = pd.DataFrame(map(lambda x: x.to_dict(), results.hits.hits))
    if not '_source' in df:
        hits_list = []
    else:
        df = (
            pd.concat([df, pd.json_normalize(df._source)],
                        axis=1)
            .rename(columns={'highlight': 'highlights', 'abstract': 'content'})
            .drop(columns=['_index','_source'])
            .where(lambda x: x.notnull(), None)
        )
        df.drop('_id', axis=1, inplace=True)
        hits_list = df.to_dict(orient='records')
    
    output = {
        "hits": hits_list,
        "stats": {
            "value": count,
            "relation": "eq",
            "took": results.took,
        },
        "query": {
            "keywords": keywords,
            "query_type": "web",
            "changed": False,
            "en_keywords": keywords,
            "aug_keywords": aug_keywords,
            "contains_fr": False
        }
    }
    return output




class ESManager(object):
    """
    To use for holding connections to elasticsearch clusters.
    """
    def __init__(
        self, 
        hosts,
        username='username',
        password='password',
        verify_certs=True,
        timeout=160,
        use_async=False):
        """
        Init Elastic search manager.

        :param hosts (list): A list of host adresses
        :param access_key (str, optional): access key
        :param secret_key (str, optional): secret key
        :param region (str, optional): region
        :param service (str):
        """
        self.auth = username, password

        if not use_async:
            self.connect = Elasticsearch(
                hosts,
                timeout=timeout,
                http_auth = self.auth,
                verify_certs = False,
            )
        else:
            self.connect = AsyncElasticsearch(
                hosts=hosts,
                timeout=timeout,
                http_auth = self.auth,
                verify_certs = verify_certs,
            )
        self.index = os.environ.get('ES_INDEX')




    def search(
        self,
        index: str = '',
        query: Q = None,
        sources: List = [],
        highlight: Dict = {},
        sort: List[Any] = None,
        extras: Dict = {},
        **kwargs: Any
    ):
        """
        Execute search query.

        :param index: (str) index name
        :param query: (Dict) query
        :param sources: (List) sources
        :param highlight: (Dict) highlight
        :param sort: (List[Any]) list of dicts or str
        :param extras: (Dict) extras
        """
        self.index = index if len(index.strip()) > 0 else self.index
        _s = sch.Search(using=self.connect, index = self.index).extra(**extras).query(query)
        
        if len(highlight.keys()):
            fields = highlight.pop('fields', {})
            _s = _s.highlight_options(**highlight)
            for field, highlight_options in fields.items():
                _s = _s.highlight(field, **highlight_options)
        
        if len(sources) > 0: _s = _s.source(sources)
        if sort: _s = _s.sort(*sort)

        resp = _s.execute(ignore_cache=False)

        return resp
    



def es_connection(
    login: Optional[str] = os.environ.get('ES_LOGIN'),
    password: Optional[str] = os.environ.get('ES_PASSWORD'),
    host: Optional[str] = os.environ.get('ES_HOST'),
    verify: Optional[bool] = True
) -> ESManager:
    """
    Create ESManager connection
    :param login: str. Defaut to global variable ES_LOGIN
    :param password: str. Defaut to global variable ES_PASSWORD
    :param host: str. Defaut to global variable ES_HOST
    :param verify: bool. Verify SSL certs. Defaut to True
    :return: ESManager object
    """
    es_login, es_passwd, es_host = login, password, host
    connection = ESManager(
        hosts=es_host, username=es_login, password=es_passwd,
        use_async=False, verify_certs=verify
    )
    return connection




def search_ids_query(
    ids: List[str],
    **kwargs: Any,
) -> Dict[str, Union[str, Dict[str, str]]]:
    """
    Search articles by ids

    :param ids: (list) of ids
    :return: Dict[stats, hits]
    """
    return {
        'query': Q('ids', values=[str(x) for x in ids]).to_dict(),
        'sources': kwargs.get('source', SOURCES),
    }





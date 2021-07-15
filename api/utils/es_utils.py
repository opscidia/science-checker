# @copyright  Copyright (c) 2018-2020 Opscidia
from elasticsearch import RequestsHttpConnection
from elasticsearch_dsl import connections, Search, Q
from elasticsearch_dsl.query import MultiMatch
from os.path import dirname, join
from urllib.parse import quote
import configparser
import boto3
from requests_aws4auth import AWS4Auth
from tqdm.auto import tqdm
from pandas import DataFrame


def local_connection():
    return connections.create_connection(hosts=['localhost:9200'], timeout=20)

def connect_to_cluster():
    config = configparser.ConfigParser()
    config.read(root + "conf/conf.ini")
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, config['ES']['REGION'], service, session_token=credentials.token)

    c = connections.create_connection(
        hosts=[config['ES']['HOST']],
#        timeout=20,
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    return c

def get_index_as_dict(index):
#     s = Search().index(index=index).scan()
    s = Search(index=index).scan()
    l=[]
    for hit in tqdm(s):
        l.append(hit.to_dict())
    return l


def hit_to_dict(hit):
    doc = hit.to_dict()
    doc['id'] = hit.meta.to_dict().get('id')
    doc['highlight'] = sum(
            list(hit.meta.to_dict().get("highlight", {}).values()),
            list())
    return doc


def get_url(doi):
    """
    Solve DOI to get the URL
    :doi: str, None
    :return: str, None
    """
    url = None
    if doi:
        doi = quote(str(doi), safe = '')
        url = "https://www.doi.org/" + doi
    return url

def index_count(index):
    query = {
        "_source": ["_type"],
        "query": {
            "match_all": {}
        }
    }
    s = Search().index(index=index).from_dict(query)
    r=s.scan()
    print("search")
    return len([1 for i in r])


def match_abstract(terms):
    """
    Create query for list of terms to search in abstract
    terms: [str, ...]
    :return: elasticsearch_dsl.query.Bool
    """
    terms = map(lambda x:x.split(' '), terms)
    listed_match = list()
    for term in terms:
        if len(term) > 1:
            query = Q('bool', must = [Q('match', abstract = word) for word in term])
        else:
            query = Q('match', abstract = term[0])
        listed_match.append(query)
    return Q('bool', should = listed_match)


def get_articles(w, keywords, index):
    """
    Get articles details from ES. Return a sigle DOI
    :w: str, concept name
    :keywords: str, ontology keywords
    :index: str
    :return: list of dict
    """
    review_list = [
        ("review", 1),
        ("feature article", .5)
#        ("survey", .5)
    ]

    should_k = [
        Q('multi_match', query = rw[0], fields = ['title', "abstract"], boost = rw[1])
        for rw in review_list if rw[0] != w
    ]

    if keywords:
        keywords = [kw for kw in keywords.split(',') if kw != w]
        should_k += [Q('multi_match', query = kw, boost = 2) for kw in keywords]

    query = Q('bool',
        must = [Q('multi_match', query = w)],
        should = should_k,
        minimum_should_match = 1 if keywords else None
    )
    
    request = Search(index = index)
    request = request.query(query)
    request = request.sort("_score")
    request = request.source([
            'DOI',
            'title',
            'URL',
            'authors',
            'abstract',
            'provider',
            'provider_id',
            'publication_date'
            ])
    request.execute()
    
    if request.count() < 10000:
        results = [
            hit.to_dict() for hit in request[:request.count()]
            ]
    else:
        results = [
            hit.to_dict() for hit in request[:9999]
            ]
    
    for hit in results:
        hit['DOI'] = get_url(hit['DOI']) if hit.get('DOI') else hit.get('URL')
        hit['review'] = any(rw[0] in hit.get('title', '').lower() for rw in review_list)
    
    return results


def get_terms_articles(measure, labels, index, **kwargs):
    """
    Get Articles from ES
    
    measure: str.
    labels: [str, ]. List of labels
    index: str. ES index.
    ci: bool. Look for confidence intervals. Default: False
    source: [str, ]. List of fields to fetch. Default: [DOI, URL, title, authors, abstract, publication_date]
    ci_terms: [str, ]. List of case insensitive terms defining CI. Default: [confidence interval, CI]
    fields: [str, ]. List of fields to highlight. Default: [abstract]
    limit: int. maximum number of hits
    
    :return: [hit, ]. List of hits in dictionary format
    """
    
    labels = [labels] if isinstance(labels, str) else labels
    source = kwargs.get('source', ['DOI', 'URL', 'title', 'authors', 'abstract', 'publication_date'])
    ci = kwargs.get('ci', False)
    ci_terms = kwargs.get('ci_terms', ['confidence interval', 'CI'])
    fields = kwargs.get('fields', ['abstract'])
    limit = kwargs.get('limit', 10_000)
    measures = measure.lower().split(' ') # split into list of lower words
    labels = sum(map(lambda x:x.lower().split(' '), labels), list()) # split into list of lower words

    query_measure = [
        Q('match', abstract_clean = word)
        for word in measures]
    if ci: query_measure.append(match_abstract(ci_terms))

    query_label = [
        Q('match', abstract_clean = label)
        for label in labels]

    query = Q('bool',
        must = query_measure,
        should = query_label,
        minimum_should_match = 1)
    
    connect_to_cluster()
    request = (
        Search(index = index)
        .query(query)
        .source(source)
        .highlight(
            *fields,
            require_field_match = False,
            boundary_scanner = "sentence",
            type = "unified",
            fragment_size = 300)
    )
    
    count = request.count()
    request.execute()
    results = list(map(
        hit_to_dict,
        request[:count] if count < limit else request[:limit-1]
    ))
    
    return results


def get_articles_from_query(query, index, labels, type_val, fields, to_csv=False):
    """
    Get the articles corresponding to the query from index
    query: (str) searched expression
    index: (str)
    fields: (str or list) for highlight fields
    :return: (list) [{title: (str), text: (list)}]
    """
    
    if isinstance(fields, str):
        fields = [fields]

#    search_dict = {
#        "_source": ["title", "abstract", "publication_date"],  
#        "query": {
#            "bool": {
#            "must": [
#                {
#                    "multi_match": {
#                        "query": f"{query} {labels}",
#                        "operator": "and",
#                        "fields": fields
#                    }
#                }
#            ]
#            
#            }
#        }
#    }

    search_dict = {
        "_source": ["title", "abstract", "publication_date"],  
          "query": { 
            "bool": {
                "must": [
                    {
                        "match": {
                            "abstract_clean": f"{query}"
                        }
                    },
                    {
                        "match": {
                            "abstract_clean": f"{labels}"
                        }
                    }
                ]
            }
          }
        }

    search = Search().from_dict(search_dict).index(index)
    search.execute()

    hits = [{**hit.to_dict(), **{"_id": hit.meta.id}} for hit in search.scan()]
    return hits

def get_sentences(articles, index, type_val, fields, to_csv=False):

    ids = [hit["_id"] for hit in articles]
    if type_val=="interval":
        fine_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "ids": {
                                "values": ids,
                            }
                        },
                        {
                            "query_string": {
                                "query": "CI OR confidence interval OR Confidence Interval OR Confidence interval OR C I",
                                "fields": [f for f in fields]
                            }
                        }
                    ]
                } 
            }
        }
        print(f"get sentences : {len(ids)} hits")
        search = Search().from_dict(fine_query).index(index)
        search.execute()
    else:
        fine_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "ids": {
                                "values": ids,
                            }
                        }
                    ]
                } 
            }
        }
        print(f"get sentences : {len(ids)} hits")
        search = Search().from_dict(fine_query).index(index)
        search.execute()
    # for field in fields:
    if to_csv:
        resp = [{
        'title': hit.title,
        'abstract': hit.abstract
        } for hit in search.scan()]
        df = DataFrame(resp)
        df.to_csv("articles.csv", index=False)
    
    search = search.highlight(
        *fields,
        boundary_scanner = "sentence",
        type = "unified",
        fragment_size = 200
        )
    
    search.execute()
    response = [{
        'title': hit.title,
        'text': sum(
            list(hit.meta.to_dict().get("highlight", {}).values()),
            list())
    } for hit in search.scan()]
    print(f"Number of highlights : {len([1 for i in response])} hits")

    return response

root = join(dirname(__file__), "../../")
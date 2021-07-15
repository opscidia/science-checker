# -*- coding: utf-8 -*-

__all__ = [
    "connect_to_cluster",
    "get_article"
]

from elasticsearch import RequestsHttpConnection
from elasticsearch_dsl import connections, Search, Q
from elasticsearch_dsl.query import MultiMatch
import boto3
from requests_aws4auth import AWS4Auth


def connect_to_cluster():
    service = 'es'
    region = 'eu-west-3'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    c = connections.create_connection(
        hosts=['https://search-opscidia-tlbsxiqbwxgyxbqyizdgdatire.eu-west-3.es.amazonaws.com'],
        timeout=20,
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    return c



def get_article(*args, get_fields = None, index = 'prod_pubmed_articles'):

    if not get_fields:
        source = ['abstract', 'fullText', 'title']
    else:
        source = list(set(get_fields + ['title']))
    
    def to_dict(r):
        d = r.to_dict()
        d['id'] = r.meta.id
        return d
    
    query = Q(
        'bool',
        must = [
            Q('multi_match', query = w, fields = ['title', 'abstract'])
            for w in args]
    )
    request = (
        Search(index = index)
        .query(query)
        .sort("_score")
        .source(source)
    )
    response = request.execute()

    return list(map(to_dict, response))
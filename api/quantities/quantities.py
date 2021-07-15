# @copyright  Copyright (c) 2018-2021 Opscidia

"""
quantities performs numerical values of interest retrieval
in relation to a topic, metrics and labels
from texts of scientific articles.
"""

__copyright__ = "Copyright 2021, Opscidia"
__status__ = "development"

import numpy as np
import pandas as pd
import re

from grobid_quantities.quantities import QuantitiesClient
from nltk.tokenize import sent_tokenize
from bs4 import BeautifulSoup
from utils.es_utils import get_terms_articles

################### GLOBAL VARIABLE ######################

RULES = [
    r'(.*?)\D(\d{1,2}\.\d{1,4})\s?(?:to|and|-)\s?(\d{1,2}\.\d{1,4})',
    r'(.*?)(?:CI)\D+(\d{1,2}\.?\d{1,4}\s?%)\s?(?:to|and|-)\s?\D(\d{1,2}\.?\d{1,4}\s?%)',
    # r'({}).*?(?:between \s)?\D+((?!0+(?:\.0+)?$)\d?\d(?:\.\d\d+)?)(?:%?)\s?(?:to|and|-)\s?((?!0+(?:\.0+)?$)\d?\d(?:\.\d\d+)?)(?:%?)',
]

################### LOCAL FUNCTIONS ######################

def html_clean(data_clean,usecols):
    
    #Insert a space after html tags to allow for html cleaning
    #html parsing
    for column in usecols:
        data_clean.loc[:, column] = data_clean[column].apply(lambda x: BeautifulSoup(str(x), 'html.parser').get_text())
    
    return (data_clean)


def interval_clean(data_clean, usecols):
    """
    Clean confidence intervals to make it easier for grobid reading
    """
    def translate(sentence):
        trans = [
            ('·', '.'),
            ('–', '-'),
            (r'(?<=\d)-(?=\d)', ' to ')
        ]
        for t in trans:
            sentence = re.sub(*t, sentence)
        return sentence

    for column in usecols:
        data_clean.loc[:, column] = data_clean[column].apply(translate)
    
    return (data_clean)



def get_data(measurement, type_val, metric):
    """
    Standardize Grobid's data output
    measurement: dict
    type_val: (str), 'value' or 'interval'
    metric: (str), 'time', 'mass', 'volume'... None
    :return: (list) [**quantity, unit] or numpy.nan
    """
    quantity = np.nan
    if metric:
        print(measurement.get('quantity', {}).get('normalizedUnit', {}).get('type'))
        if (measurement['type'], measurement.get('quantity', {}).get('normalizedUnit', {}).get('type')) == (type_val, metric):
            unit = measurement['quantity'].get('normalizedUnit', {}).get('name', np.nan)
            value = measurement['quantity'].get('normalizedQuantity', np.nan)
            quantity = [value, unit]
        elif (measurement['type'], measurement.get('quantityMost', {}).get('normalizedUnit', {}).get('type')) == (type_val, metric):
            unit = measurement.get('quantityMost', {}).get('normalizedUnit', {}).get('name', np.nan)
            valueLeast = measurement.get('quantityLeast', {}).get('normalizedQuantity', np.nan)
            valueMost = measurement.get('quantityMost', {}).get('normalizedQuantity', np.nan)
            quantity = [valueLeast, valueMost, unit]
    else:
        if measurement['type'] == type_val == 'value':
            parsed = measurement['quantity']
            unit = parsed.get('parsedValue', {}).get('structure', {}).get('type', np.nan)
            value = parsed.get('parsedValue', {}).get('numeric', np.nan)
            quantity = [value, unit]
        elif measurement['type'] == type_val == 'interval':
            parsedMost, parsedLeast = measurement.get('quantityMost', {}), measurement.get('quantityLeast', {})
            unit = parsedMost.get('parsedValue', {}).get('structure', {}).get('type', np.nan)
            valueLeast = parsedLeast.get('parsedValue', {}).get('numeric', np.nan)
            valueMost = parsedMost.get('parsedValue', {}).get('numeric', np.nan)
            quantity = [valueLeast, valueMost, unit]
            
    return quantity


def extract(text, type_val, metric):
    """
    Extract quantities from text
    type_val: (str), 'value' or 'interval'
    metric: (str), 'time', 'mass', 'volume'...
    :return: list of [**quantity, unit]
    """
    client = QuantitiesClient(apiBase='http://localhost:8060/service/')
    text = text.encode('ascii', 'ignore').decode()
    measurements = client.process_text(text)[1].get('measurements')
    quantities = [np.nan]
    if measurements:
        quantities = [get_data(measure, type_val, metric) for measure in measurements]    
    return quantities


def split_quantity(data, type_val):
    """
    Assigns columns according to measurement type
    data: (DataFrame) with measures column
    type_val: (str), 'value' or 'interval'
    :return: (DataFrame)
    """
    debug = False
    if type_val == 'value':
        columns = ['quantity', 'unit']
    else: columns = ['quantityLeast', 'quantityMost', 'unit']  
    if debug:
        data.to_csv("measures.csv", index=False)
        print(len(data.index))
    data = (data.explode('measures'))
    if debug:
        data.to_csv("measures_exploded.csv", index=False)
        print(len(data.index))
    data = (data.dropna())
    if debug:
        data.to_csv("measures_w_intervals_only.csv", index=False)
        print(len(data.index))
    
        
    try:
        data[columns] = pd.DataFrame(
            data.measures.tolist(),
            index = data.index
        )
    except ValueError:
        data[columns] = pd.DataFrame(
            columns = columns,
            index = data.index
        )
        
    data = data.drop(['measures'], axis = 1)
    return data


def get_label(data, labels):
    """
    Add the label column if it matches
    data: (DataFrame)
    labels: (list) of labels, case sensitive
    :return: (DataFrame) with label column
    """
    pattern = "|".join(labels)
    data['label'] = (
        (data['title'] + data['text'])
        .str.extract('('+pattern+')', expand = False, flags = re.I)
    )
    return data


def findnear(text: str, labels: list, pattern: str) -> list:
    """
    Find the nearest label
    """
    matches, groups = list(), dict()
    for l in labels:
        matches += re.findall(fr'({l}){pattern}', text, re.I)
    for label, s, min_, max_ in matches:
        groups[(min_, max_)] = (label, len(s)) if groups.get(
            (min_, max_), ('', 9**9))[1] > len(s) else groups.get((min_, max_))
    matches = list(map(lambda x: (x[1][0], *x[0]), groups.items()))
    return matches
    

################### MAIN FUNCTIONS #######################
def preprocessing(articles):
    """
    Returns usable data
    articles: articles from get_terms_articles
    :return: (DataFrame) w/ DOI, title, text, authors
    """

    data_clean = (
        pd
        .DataFrame(articles)
        [['id', 'DOI', 'title', 'abstract', 'authors', 'URL']]
        #.rename(columns = {'highlight': 'text'})
        # .explode('text')
        .rename(columns={"abstract":"text"}) # w/out HG
        .pipe(html_clean, ['text'])
        .pipe(interval_clean, ['text'])
    )
    
    data_clean['text'] = data_clean.text.apply(sent_tokenize)
    data_clean = (
        data_clean
        .explode('text')
        .reset_index(drop = True)
    )
    

    return data_clean


def gather(data, metric, type_val, labels):
    """
    Collect quantities of interest
    data: (DataFrame) w/ title, text
    metric: (str)
    type_val: (str) 'value' or 'interval'
    labels: (list) of labels, case sensitive
    """
    gathered = (
        data
        .assign(measures = data.text.apply(extract, args=(type_val, metric)))
        .pipe(split_quantity, type_val)
        .pipe(get_label, labels)
    )
    return gathered


def regather(data, labels: list, patterns: list = RULES):
    """
    Collect quantities of interest with rules
    data: (DataFrame) w/ title, text
    labels: (list) of labels, case sensitive
    patterns: regex rules
    """
    
    columns = ['label', 'quantityLeast', 'quantityMost']
    data['simple'] = data.text.apply(findnear, args = (labels, patterns[0],))
    data['percent'] = data.text.apply(findnear, args = (labels, patterns[-1],)).apply(lambda y: list(map(
        lambda x: (x[0], round(float(x[1][:-1]) / 100, 3),
                round(float(x[2][:-1]) / 100, 3)) if len(x) else x, y)))
    data['measures'] = data.simple + data.percent
    data['unit'] = 'NUMBER'
    data = data.explode('measures').dropna(subset=['measures'])
    try:
        data[columns] = pd.DataFrame(
            data.measures.tolist(),
            index = data.index
        )
    except ValueError:
        data[columns] = pd.DataFrame(
            columns = columns,
            index = data.index
        )

    data[columns[1:]] = data[columns[1:]].astype('float')
    data = (data
            .drop(['measures', 'simple', 'percent'], axis = 1)
            .query(f'{columns[1]} < {columns[2]}')
            #.pipe(get_label, labels)
           )
    
    return data


def main_quantities(**kwargs):
    """
    Quantities Main function.
    Run quantities indicator
    measure: str.
    labels: str.
    index: str.
    type: str. Default interval.
    metric: str.
    extraction: str. quantities or rules. Default rules.
    """

    results = list()
    measure = kwargs.get('measure')
    labels = [kwargs.get('labels')]
    assert measure is not None and labels is not None, "Measure and labels neeeded"

    index = kwargs.get('index')
    type_val = str(kwargs.get('type', 'interval'))
    metric = kwargs.get('metric')
    use_rules = kwargs.get('extraction', 'rules') == 'rules'
    
    articles = get_terms_articles(measure, labels, index, ci = type_val == 'interval')
    if len(articles):
        articles = preprocessing(articles)
        if use_rules:
            labels += [measure]
            results = regather(articles, labels)
        else:
            results = gather(articles, metric, type_val, labels)
        results = results.where(results.notnull(), None).to_dict('records')

    return results
    
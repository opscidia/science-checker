# @copyright  Copyright (c) 2018-2021 Opscidia

"""
Scienceqa answers a closed-ended question
by extracting relevant information from the articles
"""

__copyright__ = "Copyright 2021, Opscidia"
__status__ = "development"
__all__ = [
    'load_sqa',
    'instanciate',
    'predict_sqa',
    'main_sqa'
]


import re
import numpy as np
import pandas as pd
from typing import Tuple, Union, List, Dict

from utils.es_utils import get_terms_articles
from .sampler import Sampler
from .modeling import (
    AbstractiveQA,
    BertExtractiveQA,
    BertBooleanQA,
    BaseInterpret
)


def highlight(terms, text):
    """
    Highlight terms in text
    tarms: list of str
    text: str
    :return: str, higlighted text
    """
    terms = list(map(lambda x:re.sub(r'([.()])', r'\\\1', x), terms))
    terms = list(map(lambda x:'(?:\s*)?'.join(x.split(' ')), terms))
    pattern = '|'.join(terms)
    pattern = rf'({pattern})'
    try:
        formated = re.sub(pattern, r'<span class="hg">\1</span>', text, flags=re.I)
    except:
        formated = text
    return formated


def load_sqa(
    classifier: str,
    puller: str = None,
    **kwargs
) -> Tuple[
        Sampler,
        Union[BertBooleanQA, BaseInterpret],
        Union[BertExtractiveQA, AbstractiveQA, BaseInterpret, None]
    ]:
    """
    Load sampler and models

    puller: str. Model weights path for pulling
    classifier: str. Model weights path for classifier
    extractor: str. One of eqa, bqa or None. Default eqa
    interpret: bool. Use Quantized model. Default True

    :return: sampler, classifier model, puller model
    """
    extractor = kwargs.get('extractor', 'eqa')
    interpret = kwargs.get('interpret', True)

    if extractor == 'eqa':

        sampler = Sampler(
            boolean_tokenizer = classifier,
            extractive_tokenizer = puller,
            **kwargs
        )
        if interpret:
            puller = BaseInterpret().from_pretrained(puller)
            classifier = BaseInterpret().from_pretrained(classifier)
        else:
            puller = BertExtractiveQA.from_pretrained(puller)
            classifier = BertBooleanQA.from_pretrained(classifier)

    elif extractor == 'bqa':

        sampler = Sampler(
            boolean_tokenizer = classifier,
            abstractive_tokenizer = puller,
            **kwargs
        )
        if interpret:
            raise NotImplementedError("AbstractiveQA is not quantized")
        else:
            puller = AbstractiveQA.from_pretrained(puller)
            classifier = BertBooleanQA.from_pretrained(classifier)
    
    else:

        sampler = Sampler(
            boolean_tokenizer = classifier,
            **kwargs
        )

        puller = None
        if interpret:
            classifier = BaseInterpret().from_pretrained(classifier)
        else:
            classifier = BertBooleanQA.from_pretrained(classifier)

    return sampler, classifier, puller



def instanciate(
    first: str,
    second: str,
    relation: str,
    index: str,
    articles: list = None
) -> pd.DataFrame:
    
    question = f'Does {first} {relation} {second}?'

    if not articles:
        articles = get_terms_articles(first, second, index)
    
    if len(articles):
        articles = (
            pd.DataFrame(articles)
            .rename(columns={"abstract": "context"})
            .drop_duplicates(['title'])
            .reset_index(drop = True)
            [['title', 'context', 'id', 'DOI', 'authors', 'publication_date', 'URL']]
        )
        articles['question'] = question
    
    else:
        articles = pd.DataFrame(columns=['title', 'context', 'id', 'DOI', 'authors', 'publication_date', 'question', 'URL'])

    return articles


def predict_sqa(
    articles: pd.DataFrame,
    sampler: Sampler,
    classifier: Union[BertBooleanQA, BaseInterpret],
    puller: Union[BertExtractiveQA, AbstractiveQA, BaseInterpret, None],
    **kwargs
) -> List[Dict]:

    """
    Answer to question

    articles: pandas DataFrame.
    sampler: Sampler.
    classifier: BooleanQA.
    puller: ExtractiveQA or AbstractiveQA.
    batch_size: int. Batch size for puller predicting. Default 1
    max_length: int. AbstractiveQA max_lenght generation. Default 80
    num_beams: int. AbstractiveQA num_beams. Default 3
    no_repeat_ngram_size: int. AbstractiveQA arg. Default 2

    :return: list. of answers per article
    """
    question = articles.reset_index(drop=True).question[0]
    batch_size = kwargs.get('batch_size', 1)
    readable = list()

    interpret = isinstance(classifier, BaseInterpret)
    extractor = 'eqa' if isinstance(puller, (BertExtractiveQA, BaseInterpret)) else 'bqa'
    extractor = extractor if puller else None

    if extractor == 'eqa':
        context_eqa, _id, title, ext_end_ids, details = sampler.to_predict_extractive_dataset(
            articles, to_interpret = True)
        doi, authors, urls, date = details
        response_ext = puller.predict(
            context_eqa, batch_size = batch_size,
            use_multiprocessing = True
        )

        context, end_ids, selected = sampler.to_predict_boolean_dataset(
            response_ext, context_eqa, from_ext = True,
            from_interpret = True, to_interpret = True,
            question = question, return_selected = True,
            end_context = ext_end_ids
        )

        answers = classifier.predict(context, batch_size = batch_size)

        decoded_ext = sampler.tok_ext.batch_decode(selected)
        h_responses_ext = [
                sampler.unique_sent(decoded_ext[start:end])
            for start, end in zip([0]+ext_end_ids[:-1], ext_end_ids)]
        articles['terms'] = h_responses_ext
        h_responses_ext = articles.apply(lambda x:highlight(x.terms, x.context), axis=1).to_list()

        if interpret:
            h_answers_ext = [{"no": round(r[0][0][0]*100,2),
            "yes": round(r[0][0][1]*100,2),
            "neutral": round(r[0][0][2]*100,2)}
            for r in answers]
        else:
            h_answers_ext = [{"no": round(r[0]*100,2),
            "yes": round(r[1]*100,2),
            "neutral": round(r[2]*100,2)}
            for r in answers.tolist()]
            

        readable = [{
            "question": question,
            "_id": _id[i],
            "DOI": doi[i],
            "title": title[i],
            "authors": authors[i],
            "date": date[i],
            "URL": urls[i],
            "response": h_responses_ext[i],
            "answer": h_answers_ext[i]
        } for i in range(len(title))]
    
    elif extractor == 'aqa':

        max_length = kwargs.get('max_length', 80)
        num_beams = kwargs.get('num_beams', 3)
        no_repeat_ngram_size = kwargs.get('no_repeat_ngram_size', 2)

        context, _id, title, abs_end_ids, doi, authors, date = sampler.to_predict_abstractive_dataset(articles)
        responses_abs = puller.batch_generate(
            context, batch_size = batch_size,
            max_length = max_length, num_beams = num_beams,
            no_repeat_ngram_size = no_repeat_ngram_size, 
            early_stopping = True
        )

        context, end_ids = sampler.to_predict_boolean_dataset(
            responses_abs, from_abs = True,
            question = question,
            end_context = abs_end_ids
        )
        answers = classifier.predict(context, batch_size = batch_size)

        decoded_abs = sampler.tok_abs.batch_decode(responses_abs)
        h_responses_abs = [
            ". ".join(decoded_abs[start:end])
            for start, end in zip([0]+abs_end_ids[:-1], abs_end_ids)]

        if interpret:
            h_answers_abs = [{"no": round(r[0][0][0]*100,2),
            "yes": round(r[0][0][1]*100,2),
            "neutral": round(r[0][0][2]*100,2)}
            for r in answers]
        else:
            h_answers_abs = [{"no": round(r[0]*100,2),
            "yes": round(r[1]*100,2),
            "neutral": round(r[2]*100,2)}
            for r in answers.tolist()]
            

        readable = [{
            "question": question,
            "_id": _id[i],
            "DOI": doi[i],
            "title": title[i],
            "authors": authors[i],
            "date": date[i],
            "response": h_responses_ext[i],
            "answer": h_answers_ext[i]
        } for i in range(len(title))]
    
    else:

        context, end_ids = sampler.to_predict_boolean_dataset(articles)
        answers = classifier.predict(context, batch_size = batch_size)

        responses_bool = [np.mean(answers[start:end], axis = 0)
            for start, end in zip([0]+end_ids[:-1], end_ids)]

        if interpret:
            h_answers_bool = [{"no": round(r[0][0][0]*100,2),
            "yes": round(r[0][0][1]*100,2),
            "neutral": round(r[0][0][2]*100,2)}
            for r in answers]
        else:
            h_answers_bool = [{"no": round(r[0]*100,2),
            "yes": round(r[1]*100,2),
            "neutral": round(r[2]*100,2)}
            for r in responses_bool]

        readable = [{
            "question": question,
            "_id": articles.id[i],
            "DOI": articles.DOI[i],
            "title": articles.title[i],
            "authors": articles.authors[i],
            "date": articles.publication_date[i],
            "response": None,
            "answer": h_answers_bool[i]
        } for i in range(len(articles.title))]
    
    return readable


def main_sqa(**kwargs) -> List[Dict]:
    """
    ScienceQA Main function.
    Run SQA indicator

    first: str.
    second: str.
    relation: str.
    index: str.
    sampler: Sampler.
    classifier: BooleanQA.
    puller: ExtractiveQA or AbstractiveQA.
    limit: int. Default 100.
    page: int. Default 1.
    **kwargs: predict_sqa kwargs

    :return: list.
    """
    
    limit = kwargs.get('limit', 100)
    page = kwargs.get('page', 1)
    
    results = list()
    first, second = kwargs['first'], kwargs['second']
    relation = kwargs['relation']
    index = kwargs['index']
    sampler = kwargs.pop('sampler')
    classifier, puller = kwargs.pop('classifier'), kwargs.pop('puller')

    articles = instanciate(first, second, relation, index)
    articles = articles.iloc[limit*(page-1):limit*page]
    if len(articles):
        results = predict_sqa(articles, sampler, classifier, puller, **kwargs)
    
    return results
# -*- coding: utf-8 -*-
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import backend as K

import re
from pprint import pprint as cat

from utils import (
    BooleanQA,
    AbstractiveQA,
    ExtractiveQA,
    Sampler
)
from utils.es_retrieve import (
    connect_to_cluster,
    get_article
)


BOOLEAN_MODEL = "data/weights/boolean-qa/"
ABSTRACTIVE_MODEL = "data/weights/s-abstractive-qa/"
EXTRACTIVE_MODEL = "data/weights/extractive-qa/"
BATCH_GENERATE_SIZE = 12
BATCH_EXTRACT_SIZE = 16
FIELDS = ['abstract']



def extract_q(question):
    """
    Extract kewords from question
    """
    extract = re.compile(r'\w+ ([\w].*) (?:increase|cause|prevent|cure) ([\w].*)\?')
    return extract.findall(question)[0]


def gathering(question):
    connect_to_cluster()
    articles = get_article(
        *extract_q(question),
        get_fields = FIELDS
    )
    articles = (
        pd.DataFrame(articles)
        .rename(columns={"abstract": "context"})
        .drop_duplicates(['title'])
    )
    articles['question'] = question
    return articles


def abstractive_pipeline(question, model, boolQA, sampler):
    """
    BooleanQA using AbstractiveQA for informations retrieval
    :param question: str, question
    :param model: AbstractiveQA model
    :param boolQA: BooleanQA model
    :param sampler: Sampler with model and boolQA tokenizers
    :return: list of dict
    """
    # Articles data from ES
    articles = gathering(question)

    # Informations extraction
    context, _id, title, abs_end_ids = sampler.to_predict_abstractive_dataset(articles)
    responses = model.batch_generate(
        context, batch_size = BATCH_GENERATE_SIZE,
        max_length = 80, num_beams = 3,
        no_repeat_ngram_size = 2, 
        early_stopping = True
    )

    # Boolean answer classification
    context, end_ids = sampler.to_predict_boolean_dataset(
        responses, from_abs = True,
        question = question,
        end_context = abs_end_ids
    )
    answers = boolQA.predict(context)

    # Formating all data
    decoded = sampler.tok_abs.batch_decode(responses)
    h_responses = [
        " ".join(decoded[start:end])
        for start, end in zip([0]+abs_end_ids[:-1], abs_end_ids)]
    h_answers = [{
        "no": round(r[0]*100,2),
        "yes": round(r[1]*100,2),
        "neutral": round(r[2]*100,2)
    } for r in answers.tolist()]
    readable = [{
        "question": question,
        "_id": _id[i],
        "title": title[i],
        "response": h_responses[i],
        "answer": h_answers[i]
    } for i in range(len(title))]

    return readable



def extractive_pipeline(question, model, boolQA, sampler):
    """
    BooleanQA using ExtractiveQA for informations retrieval
    :param question: str, question
    :param model: AbstractiveQA model
    :param boolQA: BooleanQA model
    :param sampler: Sampler with model and boolQA tokenizers
    :return: list of dict
    """
    # Articles data from ES
    articles = gathering(question)

    # Informations extraction
    context_eqa, _id, title, ext_end_ids = sampler.to_predict_extractive_dataset(articles)
    response_ext = model.predict(
        context_eqa, batch_size = BATCH_EXTRACT_SIZE,
        use_multiprocessing = True
    )

    # Boolean answer classification
    context, end_ids, selected = sampler.to_predict_boolean_dataset(
        response_ext, context_eqa, from_ext = True,
        question = question, return_selected = True,
        end_context = ext_end_ids
    )
    answers = boolQA.predict(context)

    # Formating all data
    decoded_ext = sampler.tok_ext.batch_decode(selected)
    h_responses_ext = [
        " ".join(decoded_ext[start:end]).split('</s>')[-1]
        for start, end in zip([0]+ext_end_ids[:-1], ext_end_ids)]
    h_answers_ext = [{"no": round(r[0]*100,2),
    "yes": round(r[1]*100,2),
    "neutral": round(r[2]*100,2)}
    for r in answers.tolist()]
    readable = [{
        "question": question,
        "_id": _id[i],
        "title": title[i],
        "response": h_responses_ext[i],
        "answer": h_answers_ext[i]
    } for i in range(len(title))]

    return readable


def boolean_pipeline(question, boolQA, sampler):
    """
    BooleanQA with no informations retrieval
    :param question: str, question
    :param boolQA: BooleanQA model
    :param sampler: Sampler with boolQA tokenizers
    :return: list of dict
    """
    # Articles data from ES
    articles = gathering(question)

    # Boolean answer classification
    context, end_ids = sampler.to_predict_boolean_dataset(articles)
    answers = boolQA.predict(context)

    # Formating all data
    responses_bool = [np.mean(answers[start:end], axis = 0)
        for start, end in zip([0]+end_ids[:-1], end_ids)]
    h_answers_bool = [{"no": round(r[0]*100,2),
        "yes": round(r[1]*100,2),
        "neutral": round(r[2]*100,2)}
        for r in responses_bool]
    readable = [{
        "question": question,
        "_id": articles.id[i],
        "title": articles.title[i],
        "answer": h_answers_bool[i]
    } for i in range(len(articles.title))]

    return readable


if __name__ == "__main__":

    bqa = BooleanQA.from_pretrained(BOOLEAN_MODEL)
    aqa = AbstractiveQA.from_pretrained(ABSTRACTIVE_MODEL)
    eqa = ExtractiveQA.from_pretrained(EXTRACTIVE_MODEL)
    samplerAQA = Sampler(
        boolean_tokenizer = BOOLEAN_MODEL,
        abstractive_tokenizer = ABSTRACTIVE_MODEL
    )
    samplerEQA = Sampler(
        boolean_tokenizer = BOOLEAN_MODEL,
        extractive_tokenizer = EXTRACTIVE_MODEL
    )

    question = "Does sugar increase diabetes?"

    print('='*80)
    print('ABSTRACTIVE BOOLEAN MODEL')
    print('_'*80)

    answer = abstractive_pipeline(
        question,
        aqa, bqa,
        samplerAQA
    )
    print()
    cat(answer)

    print('='*80)
    print('EXTRACTIVE BOOLEAN MODEL')
    print('_'*80)

    answer = extractive_pipeline(
        question,
        eqa, bqa,
        samplerEQA
    )

    cat(answer)

    print('='*80)
    print('SIMPLE BOOLEAN MODEL')
    print('_'*80)

    answer = boolean_pipeline(
        question,
        bqa,
        samplerEQA # Any sampler with boolean_tokenizer works
    )

    cat(answer)

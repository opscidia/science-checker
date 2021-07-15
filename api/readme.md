<!-- @copyright  Copyright (c) 2018-2020 Opscidia -->
# Opscidia API service

> displays useful information computed from scientific publications. See `preprocess` folder for scripts useful to retrieve and clean the data that will be used in this computational modules.

## Installation

    sudo apt-get install python3
    pip install -r requirements.txt

The folders `data` and `conf` should be installed at the same level as the `api` folder.

To launch the API

    cd api/
    screen -S API
    python api_opscidia.py

Then you can quit session (CTRL A + CTRL D)

To come back to screen use

    screen -r API

In case of trouble, list sessions with :

    screen -list

For quantities module:

    sudo apt install nvidia-cuda-toolkit
    
https://pytorch.org/get-started/locally/

## API Call examples

To test the installation you can use :

    curl "http://localhost:5000/api/v1/resources/ontology/?keywords=nlp&head=3&depth=3&index=openaire-entities&ner=0&model=Computer%20Science%20%28303%20215%29"

## Modules

### Ontology

Build an ontology on certain keywords, based on an embeddings model, also possible to filter on certain tags from the NER step.

See [Module Ontology schema](https://docs.google.com/drawings/d/1zdwQrKoeNLSXk9pPkxEnvBM5-CpRKPGgBpJIr_1th9U/edit?usp=sharing) for details.

### Articles

Retrieve articles from ES index following different options (review or not, etc.)

### Indicators

Calculate an estimation of the research activity based on the publications activity for a given topic.

### Quantities

This folder contains scripts based on Grobid Quantities tools (https://grobid-quantities.readthedocs.io). It enables to retrieve numerical data (measurements) from corpus.

## Common utils

    - *model_utils.py* : contains the functions allowing to interact with the models (load)
    - *es_utils.py* : connectors and usefull functions for ES data management

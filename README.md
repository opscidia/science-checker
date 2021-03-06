# Science checker
Science checker project w/ Vietsch Foundation

The present project, called Opscidia Science Checker, aims at developing a tool to verify scientific claims by analyzing the pertinent and available scientific literature. The subject of fake news is a very topical one. With social networks, and the advances of artificial intelligence, it is easier and easier to create fake news, and they circulate quicker and quicker. Health is a particularly nasty topic for fake news. Scam medicine, and worrisome information circulate, often based on absolutely no scientific evidence.. The main idea of this project is to build several indicators based on the analysis of very large volumes of scientific articles. These indicators will be easy to understand in order for the non-specialist to have a quick idea of whether an information is backed by the scientific literature, is under debate, or is totally groundless.   The tool developed will be of use for journalists and media groups as well as for the general public. The idea actually emerged after a discussion with a scientific journalist who conducts long investigations on cases of possible fake medicine. The use of tools such as ours would be very useful to help them target the topics that deserve investigation, and would give a starting point for their work. We have further discussed this topic with several other journalists that all showed a very strong interest for the development of such a product. 

## Requirements

```
boto3
elasticsearch
elasticsearch-dsl
fastapi
grobid-quantities-client
nltk
numpy
pandas
requests-aws4auth
sentencepiece
tensorflow
transformers
uvicorn
```

## Run demo
```python
python scienceqa/main.py
```

## Docker Mount
Add weights to `data/weights/<model-name>`.  
Model weights should contains, at least:

- `config.json`
- `tf_model.h5`
- `vocab.json`
- `tokenizer_config.json`
- `merges.txt`
- `special_tokens_map.json`

Set correct parameters in `env.prod`

Then, deploy with
```bash
./mount.sh
```

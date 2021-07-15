# -*- coding: utf-8 -*-

__copyright__ = "Copyright (c) 2018-2020 Opscidia"
__maintainer__ = "Loic Rakotoson"
__status__ = "Development"
__all__ = [
    "Sampler"
]


import numpy as np
import pandas as pd
import tensorflow as tf
import transformers as tr
from tensorflow.keras import backend as K
from tensorflow.python.framework import ops

import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize


AUTO = tf.data.experimental.AUTOTUNE


class Sampler:
    def __init__(self,
                 boolean_tokenizer,
                 abstractive_tokenizer=None,
                 extractive_tokenizer=None,
                 **kwargs):
        """
        Sampler handle formating, tokenizer and bridge between models
        :param *_tokenizer: model name, path or tokenizer model
        :param *_length: encoder, decoder and boolean tokenizers lengths
        :param window_size: number of sentence per window
        :param window_stride: moving step. High value is better for abstractive
            while low value yield more data for extractive
        """
        
        self.encoder_length = kwargs.get('encoder_length', 512)
        self.decoder_length = kwargs.get('decoder_length', 80)
        self.boolean_length = kwargs.get('boolean_length', 512)
        self.extract_length = kwargs.get('extract_length', 300)
        
        if extractive_tokenizer:
            self.window_size = kwargs.get('window_size', 5)
            self.window_stride = kwargs.get('window_stride', 2)
        else:
            self.window_size = kwargs.get('window_size', 10)
            self.window_stride = kwargs.get('window_stride', 10)
            
        self.get_tokenizers(boolean_tokenizer, abstractive_tokenizer,
                            extractive_tokenizer)

    def get_tokenizers(self, tok_bool, tok_abs, tok_ext):
        def assign(tok):
            if isinstance(tok, str):
                tok = tr.AutoTokenizer.from_pretrained(tok)
            return tok

        if not (tok_abs or tok_ext):
            print("""
                Only boolean tokenizer was initialised.
                Ignore this message if the boolean_pipeline will be used, otherwise
                use at least one of abstractive_tokenizer or extractive_tokenizer
            """)

        self.tok_bool = assign(tok_bool)
        self.tok_abs = assign(tok_abs)
        self.tok_ext = assign(tok_ext)

        
    def window(self, sentences):
        return [
            sentences[w:w + self.window_size]
            for w in range(0, len(sentences), self.window_stride)
        ]
    
    
    def to_context(self, question, text):
            return list(map(
                lambda x:f'question: {question} </s> context: {" ".join(x)} </s>',
                self.window(sent_tokenize(text))
            ))
    
    @staticmethod
    def tensor_window(a, size):
        shape = a.shape[:-1] + (a.shape[-1] - size + 1, size)
        strides = a.strides + (a. strides[-1],)
        return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)

        
    @staticmethod
    def to_train_dataset(data):
        cols = {"question", "context", "answer"}
        def context(q, c):
            q = q.encode().decode("utf8")
            c = c.encode().decode("utf8")
            return f'question: {q} </s> context: {c} </s>'
        
        assert isinstance(data, pd.DataFrame), "only pandas.DataFrame supported"
        assert cols.issubset(data), f"data must contains {cols} columns"
        
        data['f_context'] = data.apply(
            lambda x: context(x.question, x.context),
            axis = 1
        )
        
        return data
    
    
    @staticmethod
    def to_predict_dataset(data):
        cols = {"question", "context"}

        assert isinstance(
            data,
            (pd.DataFrame, ops.EagerTensor, tf.RaggedTensor, list)
        ), "only pandas.DataFrame, list of arrays, EagerTensor and RaggedTensor supported"
        if isinstance(data, pd.DataFrame):
            assert cols.issubset(data), f"data must contains {cols} columns"

    
    def to_train_abstractive_dataset(self, data, batch_size = 16, buffer = 1e4):
        """
        format pandas.DataFrame to create dataset for training AbstractiveQA
        :param data: dataframe with question, context and answer
        :param batch_size: batch size
        :param buffer: buffer for shuffle
        :return: tensorflow dataset of (n, encode_length) size
        :rtype: tf.Tensor
        """
        data = self.to_train_dataset(data)

        def answer(a):
            return f'{a.encode().decode("utf8")} </s>'

        data['f_answer'] = data.apply(lambda x: answer(x.answer), axis=1)

        cont = self.tok_abs.batch_encode_plus(
            data['f_context'].to_list(),
            truncation = True,
            return_tensors = 'tf',
            max_length = self.encoder_length,
            padding = "max_length")
        ans = self.tok_abs.batch_encode_plus(
            data['f_answer'].to_list(),
            truncation = True,
            return_tensors = 'tf',
            max_length = self.decoder_length,
            padding = "max_length")
        
        data = {'input_ids': cont['input_ids'], 'labels': ans['input_ids']}
        
        dataset = (
            tf.data.Dataset
            .from_tensor_slices(data)
            .shuffle(int(buffer))
            .batch(batch_size)
            .prefetch(AUTO)
            .repeat()
        )
        
        return dataset
    
    
    def to_train_boolean_dataset(self, data, labels = None, batch_size = 16, buffer = 1e4):
        """
        format pandas.DataFrame to create dataset for training BooleanQA
        :param data: dataframe with question, context and answer
        :param labels: dict of labels, by default {'no':0, 'yes':1, 'neutral':2}
        :param batch_size: batch size
        :param buffer: buffer for shuffle
        :return: tensorflow dataset of (n, boolean_length) size
        :rtype: tf.Tensor
        """
        
        data = self.to_train_dataset(data)
        if labels:
            assert isinstance(labels, dict), "Labels must be a dict"
            assert len(labels) == 3, "Labels must have no/yes/neutral keys"
        else:
            labels = {'no':0, 'yes':1, 'neutral':2}
        
        data['f_answer'] = data.apply(lambda x: labels.get(x.answer, 2), axis=1)
        
        cont = self.tok_bool.batch_encode_plus(
            data['f_context'].to_list(),
            truncation = True,
            return_tensors = 'tf',
            max_length = self.boolean_length,
            padding = "max_length")
        cont = K.constant(cont['input_ids'], dtype = tf.int32)
        ans = K.constant(data['f_answer'].to_list(), dtype = tf.int32)
        
        dataset = (
            tf.data.Dataset
            .from_tensor_slices((cont, ans))
            .shuffle(int(buffer))
            .batch(batch_size)
            .prefetch(AUTO)
            .repeat()
        )
        
        return dataset
    
    
    def to_train_extractive_dataset(self, data, batch_size = 16, buffer = 1e4):
        """
        format pandas.DataFrame to create dataset for training AbstractiveQA
        :param data: dataframe with question, context and answer
        :param batch_size: batch size
        :param buffer: buffer for shuffle
        :return: tensorflow dataset of (n, encode_length) size, start and end indices
        :rtype: tf.Tensor
        """
        data = self.to_train_dataset(data)
        
        def answer(a):
            return f' {a.encode().decode("utf8")} </s>'

        data['f_answer'] = data.apply(lambda x: answer(x.answer), axis=1)

        context = self.tok_ext.batch_encode_plus(
            data['f_context'].to_list(),
            truncation = True,
            max_length = self.extract_length
        )
        answer = self.tok_ext.batch_encode_plus(
            data['f_answer'].to_list(),
            return_attention_mask = False
        )['input_ids']
        answer = list(map(lambda x:x[1:-1], answer))
        
        indexes = list()
        for idx, (c, a) in enumerate(zip(context, answer)):
            indices = np.all(self.tensor_window(np.array(c), len(a)) == a, axis=1)
            start = np.mgrid[0:len(indices)][indices]
            if len(start):
                d = {
                    "f_context": data.loc[idx, 'f_context'],
                    "start": start[0],
                    "end": start[0] + len(a)
                }
                indexes.append(d)
        data = pd.DataFrame(indexes)
        
        context = self.tok_ext.batch_encode_plus(
            data['f_context'].to_list(),
            truncation = True,
            return_tensors = 'tf',
            max_length = self.extract_length,
            padding = "max_length",
            return_attention_mask = False
        )['input_ids']
        start = K.constant(data['start'].to_list(), dtype = tf.int32)
        end = K.constant(data['end'].to_list(), dtype = tf.int32)
        
        dataset = (
            tf.data.Dataset
            .from_tensor_slices((context, (start, end)))
            .shuffle(int(buffer))
            .batch(batch_size)
            .prefetch(AUTO)
            .repeat()
        )
        
        return dataset
    
    
    def to_predict_abstractive_dataset(self, data):
        """
        format pandas.DataFrame to create dataset for AbstractiveQA predict
        :param data: dataframe with question, context, title and id
        :return: context, id, title and last index of each context
        :rtype: tf.Tensor, list, list, list
        """
        
        self.to_predict_dataset(data)
        data = data.copy()
        data['context'] = data.apply(lambda x: self.to_context(x.question, x.context), axis=1)
        data['end_context'] = K.cumsum(data.apply(lambda x:len(x.context), axis=1)).numpy()
        context = self.tok_abs.batch_encode_plus(
            data.context.explode().to_list(),
            truncation = True,
            return_tensors = 'tf',
            max_length = self.encoder_length,
            padding = "max_length")['input_ids']
        
        _id, title, end_context = list(
            data[['id', 'title', 'end_context']]
            .to_dict('list').values())
        del data
        
        return context, _id, title, end_context
    
    
    def to_predict_boolean_dataset(self, data, *args, **kwargs):
        """
        format pandas.DataFrame to create dataset for BooleanQA predict
        :param data: dataframe with question, context
        :param from_abs: bool, if data is abstractiveQA output
        :param from_ext: bool, if data is extractiveQA output
        :param question: if from_abs, question string
        :param end_context: if from_abs, last index of each context
        :param return_selected: if from_ext, return extracted sequences else data
        :return: context, and last index of each context
        :rtype: tf.Tensor, list (,list)
        """
        question = kwargs.get('question')
        end_context = kwargs.get('end_context')
        from_abs = kwargs.get('from_abs')
        from_ext = kwargs.get('from_ext')
        return_selected = kwargs.get('return_selected')
        
        self.to_predict_dataset(data)
        
        if from_abs:
            assert not isinstance(data, pd.DataFrame), "abs output should be Tensor"
            assert question, "question argument needed if from_abs is True"
            assert end_context, "end_context list needed if from_abs"
            selected = data.numpy().tolist()
            context_ids = zip([0] + end_context[:-1], end_context)
            decoded = self.tok_abs.batch_decode(data)
            context = self.tok_bool.batch_encode_plus(
                [f'{question} </s> '+' '.join(decoded[start:end+1])
                for start, end in context_ids],
                truncation = True,
                return_tensors = 'tf',
                max_length = self.boolean_length,
                padding = "max_length")['input_ids']
            end_context = list(range(1, len(context)))
        
        elif from_ext:
            assert isinstance(data, list), "ext output should be list of 2 array"
            assert len(args) > 0, "data must be list of 2 array, and context is required"
            assert question, "question argument needed if from_ext is True"
            assert end_context, "end_context list needed if from_ext"

            context = args[0]
            idx = K.stack(tuple(map(lambda x: K.argmax(x, axis=1), data))).numpy().T
            selected = [x[start:end].numpy().tolist() for x, (start, end) in zip(context, idx)]
            
            decoded = self.tok_ext.batch_decode(selected)
            context_ids = zip([0] + end_context[:-1], end_context)
            context = self.tok_bool.batch_encode_plus(
                [f'{question} </s> '+' '.join(decoded[start:end+1]).split('</s>')[-1]
                for start, end in context_ids],
                truncation = True,
                return_tensors = 'tf',
                max_length = self.boolean_length,
                padding = "max_length")['input_ids']
            end_context = list(range(1, len(context)))
            
        else:
            assert isinstance(data, pd.DataFrame), "DataFrame only supported if not from_abs"
            selected = None
            data = data.copy()
            data['context'] = data.apply(lambda x: self.to_context(x.question, x.context), axis=1)
            data['end_context'] = K.cumsum(data.apply(lambda x:len(x.context), axis=1)).numpy()
            context = self.tok_bool.batch_encode_plus(
                data.context.explode().to_list(),
                truncation = True,
                return_tensors = 'tf',
                max_length = self.encoder_length,
                padding = "max_length")['input_ids']
            end_context = data.end_context.to_list()
        
        if return_selected: return context, end_context, selected
        else: return context, end_context
    
    
    def to_predict_extractive_dataset(self, data):
        """
        format pandas.DataFrame to create dataset for ExtractiveQA predict
        :param data: dataframe with question, context, title and id
        :return: context, id, title and last index of each context
        :rtype: tf.Tensor, list, list, list
        """
        
        self.to_predict_dataset(data)
        data = data.copy()
        data['context'] = data.apply(lambda x: self.to_context(x.question, x.context), axis=1)
        data['end_context'] = K.cumsum(data.apply(lambda x:len(x.context), axis=1)).numpy()
        context = self.tok_ext.batch_encode_plus(
            data.context.explode().to_list(),
            truncation = True,
            return_tensors = 'tf',
            max_length = self.extract_length,
            padding = "max_length")['input_ids']
        
        _id, title, end_context = list(
            data[['id', 'title', 'end_context']]
            .to_dict('list').values())
        del data
        
        return context, _id, title, end_context
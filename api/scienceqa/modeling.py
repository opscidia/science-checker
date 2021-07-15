# -*- coding: utf-8 -*-

__copyright__ = "Copyright (c) 2018-2020 Opscidia"
__maintainer__ = "Loic Rakotoson"
__status__ = "Development"
__all__ = [
    "AbstractiveQA",
    "BaseExtractive", "BertExtractiveQA", "RobertaExtractiveQA", "MobileExtractiveQA",
    "BaseBoolean", "RobertaBooleanQA", "BertBooleanQA"
]

from typing import List

import pandas as pd
import tensorflow as tf
import transformers as tr
from tensorflow.keras import backend as K, layers
from tensorflow.python.framework import ops
from transformers.modeling_tf_utils import (
    TFSequenceClassificationLoss,
    TFQuestionAnsweringLoss
)



class AbstractiveQA(tr.TFT5ForConditionalGeneration):
    """
    Abstractive Question Answering with language modeling head on top
    T5 Encoder-Decoder model
    Sequence output
    """

    def __init__(self, *args, log_dir = None, cache_dir = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.loss_tracker = tf.keras.metrics.Mean(name='loss') 
    
    def train_step(self, data):
        x = data
        y = x["labels"]
        y = tf.reshape(y, [-1, 1])
        with tf.GradientTape() as tape:
            outputs = self(x, training=True)
            loss = outputs[0]
            logits = outputs[1]
            loss = tf.reduce_mean(loss)
            grads = tape.gradient(loss, self.trainable_variables)
            
        self.optimizer.apply_gradients(zip(grads, self.trainable_variables))
        lr = self.optimizer._decayed_lr(tf.float32)
        
        self.loss_tracker.update_state(loss)        
        self.compiled_metrics.update_state(y, logits)
        metrics = {m.name: m.result() for m in self.metrics}
        metrics.update({'lr': lr})
        
        return metrics


    def test_step(self, data):
        x = data
        y = x["labels"]
        y = tf.reshape(y, [-1, 1])
        output = self(x, training=False)
        loss = output[0]
        loss = tf.reduce_mean(loss)
        logits = output[1]
        
        self.loss_tracker.update_state(loss)
        self.compiled_metrics.update_state(y, logits)
        return {m.name: m.result() for m in self.metrics}


    def batch_generate(self, inputs, batch_size, **kwargs):
        """
        Generates data batch per batch. Avoids resource exhaustion exceptions.
        :param inputs: tensor of token ids
        :batch_size: Size of the data to be generated at a time.
            Equivalent to the size of the resources used.
        :**kwargs: generate kwargs
        """
        generated = list()
        size = len(inputs)-1
        for i in range(0, size, batch_size):
            print('\r', end = f'{i}/{size} generated', flush = True)
            y = self.generate(inputs[i:i+batch_size], **kwargs)
            generated.append(y)
        print('\r', end = f'{size}/{size} generated', flush = True)
        tensor = tf.ragged.constant(sum(map(
            lambda x:x.numpy().tolist(),
            generated), []), dtype = tf.int32)
        return tensor


class BaseInterpret:
    """
    Interpret for Quantized model
    """
    def __init__(self):
        self

    def from_pretrained(self, path: str):
        path += '/' if path[-1] != '/' else ''
        self.model = tf.lite.Interpreter(model_path = path + "tf_model.tflite")
        self.model.allocate_tensors()
        self.input = self.model.get_input_details()
        self.output = self.model.get_output_details()
        return self
    

    def _predict(self, X: list) -> List:
        self.model.set_tensor(self.input[0]['index'], X)
        self.model.invoke()
        outputs = [
            self.model.get_tensor(details['index'])
            for details in self.output
        ]
        return outputs
    
    def predict(self, X, **kwargs) -> List:
        X = X if isinstance(X, list) else [X]
        return list(map(self._predict, X))


#########################################################################
#################            BOOLEAN MODELS             #################
#########################################################################

class BaseBoolean:
    """
    Base Model for BooleanQA
    Using CLS token representation (not pooled)
    """
    def call(
        self,
        inputs = None,
        attention_mask = None,
        token_type_ids = None,
        position_ids = None,
        head_mask = None,
        inputs_embeds = None,
        output_attentions = None,
        output_hidden_states = None,
        labels = None,
        training = False,
    ):
        outputs = self.transformer(
            inputs,
            attention_mask = attention_mask,
            token_type_ids = token_type_ids,
            position_ids = position_ids,
            head_mask = head_mask,
            inputs_embeds = inputs_embeds,
            output_attentions = output_attentions,
            output_hidden_states = output_hidden_states,
            training = training,
        )
        sequence_output = self.dropout(outputs[0], training = training)
        cls_token = self.stride(sequence_output)
        return self.bqa(cls_token)


class RobertaBooleanQA(BaseBoolean, tr.TFRobertaPreTrainedModel, TFSequenceClassificationLoss):
    """
    Boolean Question Answering with neutral label
    Using RoBERTa head
    No/Yes/Neutral outputs
    """

    _keys_to_ignore_on_load_missing = [r"pooler"]

    def __init__(self, config, *inputs, **kwargs):
        super().__init__(config, *inputs, **kwargs)
        self.num_labels = config.num_labels
        self.transformer = tr.TFRobertaMainLayer(config, name = "roberta")
        self.dropout = layers.Dropout(
            getattr(config, 'hidden_dropout_prob', .0))
        self.stride = layers.Lambda(lambda x: x[:, 0, :], name = "stride")
        self.bqa = layers.Dense(3, activation = tf.keras.activations.softmax, name = "dense")


class BertBooleanQA(BaseBoolean, tr.TFBertPreTrainedModel, TFSequenceClassificationLoss):
    """
    Boolean Question Answering with neutral label
    Using RoBERTa head
    No/Yes/Neutral outputs
    """

    _keys_to_ignore_on_load_unexpected = [
        r"mlm___cls", r"nsp___cls",
        r"cls.predictions", r"cls.seq_relationship"]
    _keys_to_ignore_on_load_missing = [r"dropout"]

    def __init__(self, config, *inputs, **kwargs):
        super().__init__(config, *inputs, **kwargs)
        self.num_labels = config.num_labels
        self.transformer = tr.TFBertMainLayer(config, name = "bert")
        self.dropout = layers.Dropout(
            getattr(config, 'hidden_dropout_prob', .0))
        self.stride = layers.Lambda(lambda x: x[:, 0, :], name = "stride")
        self.bqa = layers.Dense(3, activation = tf.keras.activations.softmax, name = "dense")

#########################################################################
#################           EXTRACTIVE MODELS           #################
#########################################################################

class BaseExtractive:
    """
    Base Model for ExtractiveQA
    """
    def call(self, inputs, **kwargs):
        outputs = self.transformer(inputs, **kwargs)
        sequence_output = self.dropout(outputs[0], training = kwargs['training'])

        start = self.start(sequence_output)
        end = self.end(sequence_output)

        start_logits = layers.Flatten()(start)
        end_logits = layers.Flatten()(end)

        start_probs = layers.Activation(tf.keras.activations.softmax)(start_logits)
        end_probs = layers.Activation(tf.keras.activations.softmax)(end_logits)
        return [start_probs, end_probs]


class BertExtractiveQA(BaseExtractive, tr.TFBertPreTrainedModel, TFQuestionAnsweringLoss):
    """
    Extractive Question Answering
    Using Bert head, whole sequence representation instead of pooler
    start, end outputs
    """
    _keys_to_ignore_on_load_unexpected = [
        r"pooler",
        r"mlm___cls",
        r"nsp___cls",
        r"cls.predictions",
        r"cls.seq_relationship",
    ]

    def __init__(self, config, *inputs, **kwargs):
        super().__init__(config, *inputs, **kwargs)
        self.num_labels = config.num_labels
        self.transformer = tr.TFBertMainLayer(
            config, add_pooling_layer = False, name = "bert")
        self.dropout = layers.Dropout(
            getattr(config, 'hidden_dropout_prob', .0))
        self.start = layers.Dense(1, name = "start", use_bias = False)
        self.end = layers.Dense(1, name = "end", use_bias = False)


class RobertaExtractiveQA(BaseExtractive, tr.TFRobertaPreTrainedModel, TFQuestionAnsweringLoss):
    """
    Extractive Question Answering
    Using Roberta head, whole sequence representation instead of pooler
    start, end outputs
    """
    _keys_to_ignore_on_load_unexpected = [r"pooler", r"lm_head"]

    def __init__(self, config, *inputs, **kwargs):
        super().__init__(config, *inputs, **kwargs)
        self.num_labels = config.num_labels
        self.transformer = tr.TFRobertaMainLayer(
            config, add_pooling_layer = False, name = "roberta")
        self.dropout = layers.Dropout(
            getattr(config, 'hidden_dropout_prob', .0))
        self.start = layers.Dense(1, name = "start", use_bias = False)
        self.end = layers.Dense(1, name = "end", use_bias = False)


class MobileExtractiveQA(BaseExtractive, tr.TFMobileBertPreTrainedModel, TFQuestionAnsweringLoss):
    """
    Extractive Question Answering
    Using MobileBert head, whole sequence representation instead of pooler
    start, end outputs
    """
    _keys_to_ignore_on_load_unexpected = [
        r"pooler",
        r"predictions___cls",
        r"seq_relationship___cls",
        r"cls.predictions",
        r"cls.seq_relationship",
    ]

    def __init__(self, config, *inputs, **kwargs):
        super().__init__(config, *inputs, **kwargs)
        self.num_labels = config.num_labels
        self.transformer = tr.TFMobileBertMainLayer(
            config, add_pooling_layer = False, name = "mobilebert")
        self.dropout = layers.Dropout(
            getattr(config, 'hidden_dropout_prob', .0))
        self.start = layers.Dense(1, name = "start", use_bias = False)
        self.end = layers.Dense(1, name = "end", use_bias = False)
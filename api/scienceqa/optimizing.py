# -*- coding: utf-8 -*-

__copyright__ = "Copyright (c) 2018-2021 Opscidia"
__maintainer__ = "Loic Rakotoson"
__status__ = "Development"
__all__ = [
    "CustomSchedule",
    "Distiller", "DistillerExtractive"
]

import tensorflow as tf
import os


class CustomSchedule(tf.keras.optimizers.schedules.LearningRateSchedule):
  def __init__(self, warmup_steps=1e4):
    super().__init__()

    self.warmup_steps = tf.cast(warmup_steps, tf.float32)
    
  def __call__(self, step):
    step = tf.cast(step, tf.float32)
    m = tf.maximum(self.warmup_steps, step)
    m = tf.cast(m, tf.float32)
    lr = tf.math.rsqrt(m)
    
    return lr


class Distiller(tf.keras.Model):
    """
    Model Distiller
    """
    def __init__(self, student, teacher):
        super(Distiller, self).__init__()
        self.teacher = teacher
        self.student = student

    def compile(
        self,
        optimizer,
        metrics,
        student_loss,
        distillation_loss,
        alpha:float = 0.1,
        temperature:float = 3,
    ):
        super(Distiller, self).compile(optimizer = optimizer, metrics = metrics)
        self.student_loss = student_loss
        self.distillation_loss = distillation_loss
        self.alpha = alpha
        self.temperature = temperature

    def train_step(self, data):
        x, y = data
        teacher_predictions = self.teacher(x, training = False)

        with tf.GradientTape() as tape:
            student_predictions = self.student(x, training = True)
            
            student_loss = self.student_loss(y, student_predictions)
            distillation_loss = self.distillation_loss(
                tf.nn.softmax(teacher_predictions / self.temperature, axis = 1),
                tf.nn.softmax(student_predictions / self.temperature, axis = 1),
            )
            loss = self.alpha * student_loss + (1 - self.alpha) * distillation_loss

        trainable_vars = self.student.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        self.compiled_metrics.update_state(y, student_predictions)

        results = {metric.name: metric.result() for metric in self.metrics}
        results.update(
            {"student_loss": student_loss, "distillation_loss": distillation_loss}
        )
        return results

    def test_step(self, data):
        x, y = data
        y_prediction = self.student(x, training=False)
        student_loss = self.student_loss(y, y_prediction)
        self.compiled_metrics.update_state(y, y_prediction)

        results = {metric.name: metric.result() for metric in self.metrics}
        results.update({"student_loss": student_loss})
        return results
    
    def save_pretrained(self, save_directory: str):
        self.student.save_pretrained(save_directory)


class DistillerExtractive(Distiller):
    def train_step(self, data):
        x, y = data
        teacher_start, teacher_end = self.teacher(x, training = False)

        with tf.GradientTape() as tape:
            student_start, student_end = self.student(x, training = True)

            student_loss_start, student_loss_end = map(
                lambda a, b: self.student_loss(a, b), y,
                [student_start, student_end])
            student_loss = student_loss_start + student_loss_end

            distillation_loss = sum(
                map(
                    lambda x, y: self.distillation_loss(
                        tf.nn.softmax(x / self.temperature, axis=1),
                        tf.nn.softmax(y / self.temperature, axis=1),
                    ), [teacher_start, teacher_end],
                    [student_start, student_end]))
            
            loss = self.alpha * student_loss + (1 - self.alpha) * distillation_loss

        trainable_vars = self.student.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        self.compiled_metrics.update_state(y, [student_start, student_end])

        results = {metric.name: metric.result() for metric in self.metrics}
        results.update({
            "student_loss": student_loss,
            "student_loss_start": student_loss_start,
            "student_loss_end": student_loss_end,
            "distillation_loss": distillation_loss
        })

        return results

    def test_step(self, data):
        x, y = data
        student_start, student_end = self.student(x, training = False)
        student_loss_start, student_loss_end = map(
            lambda a, b: self.student_loss(a, b), y,
            [student_start, student_end])
        student_loss = student_loss_start + student_loss_end
        self.compiled_metrics.update_state(y, [student_start, student_end])

        results = {metric.name: metric.result() for metric in self.metrics}
        results.update({
            "student_loss": student_loss,
            "student_loss_start": student_loss_start,
            "student_loss_end": student_loss_end
        })

        return results


class Quantizer:

    def __init__(self, model):
        self.model = model
        self.max_position_embeddings = getattr(
            model.config, 'max_position_embeddings', 300)
    
    def _convert(self, **kwargs):
        max_len = kwargs.get('max_len', self.max_position_embeddings)
        model = self.model
        input_spec = tf.TensorSpec([1,max_len], tf.int32)
        model._saved_model_inputs_spec = None
        model._set_save_spec(input_spec)
        return model

    def convert_standard(self, **kwargs):
        model = self._convert(**kwargs)
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.SELECT_TF_OPS]
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        model = converter.convert()
        return model
    
    def convert_fp16(self, **kwargs):
        model = self._convert(**kwargs)
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS, tf.lite.OpsSet.SELECT_TF_OPS]
        converter.target_spec.supported_types = [tf.float16]
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.experimental_new_converter = True
        model = converter.convert()
        return model
    
    def convert_hybrid(self, **kwargs):
        model = self._convert(**kwargs)
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS, tf.lite.OpsSet.SELECT_TF_OPS]
        converter.optimizations = [tf.lite.Optimize.OPTIMIZE_FOR_SIZE]
        converter.experimental_new_converter = True
        model = converter.convert()
        return model
    
    def convert(self, path: str, mode: str = "standard", **kwargs):
        """
        Quantize model
        :param path: str, output folder name
        :param mode: str, One of standard, fp16, hybrid. Default standard
        :param max_len: int, Input max length for batch 1. Default to model max position
        :return: None
        """
        if mode == "fp16": model = self.convert_fp16(**kwargs)
        elif mode == "hybrid": model = self.convert_hybrid(**kwargs)
        else: model = self.convert_standard(**kwargs)

        path += '/' if path[-1] != '/' else ''
        os.makedirs(path, exist_ok = True)
        with open(f'{path}tf_model.tflite', "wb") as f:
            f.write(model)
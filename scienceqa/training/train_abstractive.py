"""
Training script for AbstractiveQA
"""

import json
import numpy as np
import pandas as pd
import tensorflow as tf
from ..utils import AbstractiveQA, Sampler

# =======================================================================
# Initializing TPU if available, else auto.
# -----------------------------------------------------------------------
try:
    tpu = tf.distribute.cluster_resolver.TPUClusterResolver()
    print('Running on TPU ', tpu.master())
except ValueError:
    tpu = None

if tpu:
    tf.config.experimental_connect_to_cluster(tpu)
    tf.tpu.experimental.initialize_tpu_system(tpu)
    strategy = tf.distribute.TPUStrategy(tpu)
else:
    strategy = tf.distribute.get_strategy()

print(f"{'='*80}\nREPLICAS: {strategy.num_replicas_in_sync}\n{'='*80}")


# =======================================================================
# Data
# -----------------------------------------------------------------------
train_path = "path"
test_path = "path"
train_data = pd.read_json(train_path)
test_data = pd.read_json(test_path)


# =======================================================================
# Global variables
# -----------------------------------------------------------------------
AUTO = tf.data.experimental.AUTOTUNE
BATCH_SIZE = 6 * strategy.num_replicas_in_sync
ABSTRACTIVE_MODEL = "path" # Can be path to model or HF pretrained
FROM_PT = False # If model weight to be loaded is from Pytorch (*.bin)
WINDOW_SIZE = 10 # Use the same for production. Initialize input shape.
WINDOW_STRIDE = 10
E_LEN = 512 # Encoder max length
D_LEN = 80 # Decoder max length
NTRAIN = train_data.shape[0]
NVAL = test_data.shape[0]
STEPS = int(np.ceil(NTRAIN/BATCH_SIZE))
VAL_STEPS = int(np.ceil(NVAL/BATCH_SIZE))
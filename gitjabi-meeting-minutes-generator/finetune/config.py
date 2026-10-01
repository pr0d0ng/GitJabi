# config.py
MODEL_NAME = "monologg/koelectra-small-v3-discriminator"
NUM_LABELS = 3  # Other / Key / Action

MAX_LENGTH = 128
BATCH_SIZE = 16
EVAL_BATCH_SIZE = 32
EPOCHS = 4
LEARNING_RATE = 1e-5
WEIGHT_DECAY = 0.01

OUTPUT_DIR = "./outputs"
SEED = 42

import logging
import sys

LOG_FILE = 'log.txt'
LOG_FORMAT = '[%(asctime)s] %(levelname)-8s %(message)s'

LOGGER = None


def load_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.addHandler(console_handler)
    return logger


def get_logger():
    global LOGGER
    if not LOGGER:
        LOGGER = load_logger()
    return LOGGER

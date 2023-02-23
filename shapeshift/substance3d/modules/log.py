#!/usr/bin/env python3

import logging
import logging.config


def get_std_logger_conf():
    logger_conf = {
        'version': 1,
        'disable_existing_loggers': False,
        'loggers': {
            '': {
                'handlers': ['file'],
            },
            'noformat': {
                'handlers': ['noformat'],
                'propagate': False,
            },
        },
        'formatters': {
            'simple': {
                'format': '%(asctime)s - %(levelname)s [%(module)s]: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'noformat': {
                'format': '',
                'datefmt': '',
            },
        },
        'handlers': {
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'simple',
            },
            'noformat': {
                'class': 'logging.FileHandler',
                'formatter': 'noformat',
            },
        },
    }
    return logger_conf


def get_std_logger(log_dir):
    logger_conf = get_std_logger_conf()
    logger_conf["handlers"]["noformat"]["filename"] = f"{log_dir}/log.txt"
    logging.config.dictConfig(logger_conf)
    lgr = logging.getLogger("noformat")
    lgr.setLevel(logging.DEBUG)
    return lgr

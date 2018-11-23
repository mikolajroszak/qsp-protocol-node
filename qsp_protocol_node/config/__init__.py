####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import logging
import logging.config

from .config import config_value, Config
from .config_utils import ConfigUtils
from .config_utils import ConfigurationException
from .config_factory import ConfigFactory
from structlog import configure_once
from structlog import processors
from structlog import stdlib
from structlog import threadlocal
from os.path import expanduser
from pathlib import Path


def configure_basic_logging(verbose=False, logging_dir="/var/log"):

    logging_dir = str(logging_dir + "/qsp-protocol")
    Path(logging_dir).mkdir(parents=True, exist_ok=True)

    configure_once(
        context_class=threadlocal.wrap_dict(dict),
        logger_factory=stdlib.LoggerFactory(),
        wrapper_class=stdlib.BoundLogger,
        processors=[
            stdlib.filter_by_level,
            stdlib.add_logger_name,
            stdlib.add_log_level,
            stdlib.PositionalArgumentsFormatter(),
            processors.TimeStamper(fmt="iso"),
            processors.StackInfoRenderer(),
            processors.format_exc_info,
            processors.UnicodeDecoder(),
            stdlib.render_to_log_kwargs]
    )

    dict_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                'format': '%(message)s %(threadName)s %(lineno)d %(pathname)s ',
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
            }
        },
        'handlers': {
            'json': {
                'class': 'logging.StreamHandler',
                'formatter': 'json'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'json',
                'filename': logging_dir + '/qsp-protocol.log',
                'mode': 'a',
                'maxBytes': 10485760,
                'backupCount': 5
            }
        },
        'loggers': {
            '': {
                'handlers': ['json', 'file'],
                'level': logging.DEBUG if verbose else logging.INFO
            }
        }
    }

    logging.config.dictConfig(dict_config)


configure_basic_logging()

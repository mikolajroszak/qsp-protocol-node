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


def configure_basic_logging(verbose=False):
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)

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
            }
        },
        'loggers': {
            '': {
                'handlers': ['json'],
                'level': logging.DEBUG if verbose else logging.INFO
            }
        }
    }

    logging.config.dictConfig(dict_config)


configure_basic_logging()

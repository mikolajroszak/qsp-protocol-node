import unittest
import structlog
import logging
import logging.config
from eth.tools.logging import (
    setup_trace_logging
)


class QSPTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging()


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s[%(threadName)s] %(message)s',
    )

    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)

    structlog.configure_once(
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs]
    )
    level_map = {
        'CRITICAL': 50,
        'ERROR': 40,
        'WARNING': 30,
        'INFO': 20,
        'DEBUG': 10,
        'TRACE': 5,
        'NOTSET': 0,
    }
    dict_config = {
        'version': 1,
        'disable_existing_loggers': True,
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
                'level': level_map["DEBUG"],
            }
        }
    }
    logging.config.dictConfig(dict_config)
    setup_trace_logging()

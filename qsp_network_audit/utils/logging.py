import logging.config
import structlog

from structlog import configure, getLogger, processors, stdlib, threadlocal

def config_logging(verbose):  
  logging.config.dictConfig({
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
  })
    
  configure(
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

def getLogging():
  return getLogger("audit")

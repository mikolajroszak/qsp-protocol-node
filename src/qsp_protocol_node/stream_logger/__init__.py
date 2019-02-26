####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import structlog

__get_log_stream_provider = None
__stream_loggers = {}

def configure_once(get_log_stream_provider, force=False):
    """
    Initializes the logging.

    :param logger_config: a function providing the logging configuration
    """
    global __get_log_stream_provider
    global __stream_loggers

    if __get_log_stream_provider is not None and not force:
        raise Exception("__logger_config_wrapper can only be set once")

    __get_log_stream_provider = get_log_stream_provider
    __stream_loggers = {}


def get_logger(logger_name):
    global get_log_streamer
    global __stream_loggers    

    log_stream_provider = __get_log_stream_provider()
    if log_stream_provider is None or not log_stream_provider.config['is_enabled']:
        return structlog.get_logger(logger_name)

    # Checks if the requested logger has already been configured.
    # If so, just return it (it is a stream logger)
    logger = __stream_loggers.get(logger_name)
    if logger is not None:
        return logger

    # Otherwise, a new logger must be created, configured,
    # registered, and returned back
    
    module_logger = structlog.get_logger(logger_name)
    module_logger.addHandler(log_stream_provider.get_handler())
    __stream_loggers[logger_name] = module_logger

    return module_logger

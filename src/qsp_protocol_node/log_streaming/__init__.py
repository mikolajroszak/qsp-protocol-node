####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

import structlog

__account = None
__config = None
__stream_loggers = {}


def initialize(account, config=None, force=False):
    """
    Initializes the logging.

    :param account: The account that will be recorded in the logs
    :param config: Only the section of the file for logging
    """
    global __account
    global __config
    global __stream_loggers

    if (__config is not None or __account is not None) and not force:
        raise Exception("stream_logger configuration can only be set once")

    __config = config
    __account = account
    __stream_loggers = {}


def get_logger(logger_name):
    global __account
    global __config
    global __stream_loggers

    if __config is None or not __config.get('is_enabled', False):
        return structlog.get_logger(logger_name)

    # Checks if the requested logger has already been configured.
    # If so, just return it (it is a stream logger)
    logger = __stream_loggers.get(logger_name)
    if logger is not None:
        return logger

    # Otherwise, a need logger must be created, configured,
    # registered, and returned back
    provider = create_streaming_provider(__config.get('provider'),
                                         __config.get('args', []))
    module_logger = structlog.get_logger(logger_name)
    module_logger.addHandler(provider.get_handler())

    __stream_loggers[logger_name] = module_logger

    return module_logger


def create_streaming_provider(provider_name, provider_args):
    """
    Creates a logging provider.
    """

    # Currently we only support a single provider
    if provider_name not in ["CloudWatchProvider"]:
        raise Exception(
            "Unknown/Unsupported streaming provider: {0}".format(provider_name))

    # This local import makes a lazy initialization
    # of the streaming module (if put at the header the initialization
    # occurs immediately)

    from streaming import CloudWatchProvider
    return CloudWatchProvider(__account, **provider_args)

import logging
import logging.config
import os
import structlog

__account = None
__config = None
__stream_loggers = {}


def initialize(account, config=None):
    global __account
    global __config

    if __config is not None or __account is not None:
        raise Exception("stream_logger configuration can only be set once")

    __config = config
    __account = account


def get_logger(logger_name):
    global __account
    global __config
    global __loggers

    if __config is None or __config.get('/logging/streaming/is_enabled', False):
        return structlog.get_logger(logger_name)

    # Checks if the requested logger has already been configured.
    # If so, just return it (it is a stream logger)

    module_logger = __stream_loggers.get(logger_name)
    if module_logger is not None:
        return module_logger

    # Otherwise, a need logger must be created, configured,
    # registered, and returned back

    provider_name = __config.get('provider')

    # Currently we only support a single provider
    if provider_name not in ["CloudWatchProvider"]:
        raise Exception(
            "Unknown/Unsupported streaming provider: {0}".format(provider_name))

    provider_args = __config.get('args', [])

    # This local import makes a lazy initialization
    # of the streaming module (if put at the header the initialization
    # occurs immediately)

    from streaming import CloudWatchProvider
    provider = CloudWatchProvider(__account, **provider_args)

    handler = provider.get_handler()
    module_logger = structlog.get_logger(logger_name)
    module_logger.addHandler(handler)

    __stream_loggers[logger_name] = module_logger

    return module_logger

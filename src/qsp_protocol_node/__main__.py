####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import os
import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

print("===> sys.path is " + str(sys.path))

import stream_logger
from config import Config

import logging
import logging.config
import structlog
import traceback
import yaml

from dpath.util import get
from json import load
from pprint import pprint
from web3 import Web3


class Program:

    __yaml_config = None
    __env = None
    __version = '2.0.0'

    @classmethod
    def __setup_basic_logging(cls, level):
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
            'NOTSET': 0,
        }
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
                    'filename': '/var/log/qsp-protocol/qsp-protocol.log',
                    'mode': 'a',
                    'maxBytes': 10485760,
                    'backupCount': 5
                }
            },
            'loggers': {
                '': {
                    'handlers': ['json', 'file'],
                    'level': level_map[level],
                }
            }
        }
        logging.config.dictConfig(dict_config)


    @classmethod
    def setup(cls):
        node_version = Program.__version

        # Inject variables to be used in variable-based strings
        # in the configuration file
        config_vars = {
            'account_passwd': os.environ['QSP_ETH_PASSPHRASE'],
            'auth_token': os.environ.get('QSP_ETH_AUTH_TOKEN', ''),
            'config_file': os.environ['QSP_CONFIG'],
            'environment': os.environ['QSP_ENV'],
            'keystore_file': os.environ['QSP_KEYSTORE'],
            'major_version': node_version[0:node_version.index('.')]
        }

        Program.__setup_basic_logging(os.environ['QSP_LOGGING_LEVEL'])
        Program.__config = Config(config_vars)

        # Registers the yet to be initialized log_stream_provider
        stream_logger.configure_once(get_log_stream_provider=lambda: Program.__config.log_stream_provider)

        # Fully initializes the components in the config object (log_stream_provider included)
        Program.__config.create_components()

        print("===> config is {0}".format(Program.__config))

        Program.__logger = stream_logger.get_logger(cls.__qualname__)

    @classmethod
    def run(cls):
        """
        Runs the backend
        """
        # Note: except for stream_logger, every other import
        # to a subpackage of qsp_prototol_node must be
        # performed at this point

        from audit import QSPAuditNode
        from utils.stop import Stop

        cfg = Program.__config
        logger = Program.__logger

        logger.info("Initializing QSP Audit Node")
        logger.debug("account: {0}".format(cfg.account))
        logger.debug("analyzers: {0}".format(cfg.analyzers))
        logger.debug("audit contract address: {0}".format(cfg.audit_contract_address))

        logger.debug("min_price_in_qsp: {0}".format(cfg.min_price_in_qsp))
        logger.debug("evt_polling: {0}".format(cfg.evt_polling))
        logger.debug("audit contract address: {0}".format(cfg.audit_contract_address))

        # Based on the provided configuration, instantiates a new
        # QSP audit node
        audit_node = QSPAuditNode(cfg)
        Stop.register(audit_node)

        if audit_node.is_police_officer():
            logger.info("Running QSP node (performs audits and police checks)")
        else:
            logger.info("Running QSP node (performs audits only)")

        # If a sol file is given, produce the audit report for that file and exit
        sol_file = os.environ.get('QSP_SOL_FILE')
        if sol_file:
            _, audit_report = audit_node.get_full_report(
                requestor=cfg.account,
                uri=sol_file,
                request_id=1
            )
            pprint(audit_report)
            
        # Runs the QSP audit node in a busy loop fashion
        else:
            audit_node.run()


if __name__ == "__main__":
    logger = None
    try:
        Program.setup()
        Program.run()
    except Exception as error:
        if logger is not None:
            logger.exception("Error in running node: {0}".format(str(error)))
        else:
            traceback.print_exc()

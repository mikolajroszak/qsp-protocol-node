####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################


import logging
import logging.config
import os
import structlog
import sys
import traceback
import yaml

from dpath.util import get
from json import load
from pprint import pprint
from web3 import Web3

sys.path.append(os.path.dirname(os.path.realpath(__file__)))


class InvalidKeyStoreException(Exception):
    pass


class Program:

    __yaml_config = None
    __env = None

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
    def __setup_log_streaming(cls):
        log_streaming_config = None
        account = None
        error = None
        try:
            # Load keystore
            keystore_file = get(Program.__yaml_config[Program.__env], "/keystore_file")
            with open(keystore_file) as k:
                keystore = load(k)

            account = Web3.toChecksumAddress('0x' + keystore['address'])

            # Get log streaming config (if any)
            log_streaming_config = get(Program.__yaml_config[Program.__env], "/logging/streaming")
        except KeyError:
            error = InvalidKeyStoreException("Invalid keystore file")

        except Exception as unknown_error:
            error = unknown_error
        finally:
            # Initialize the log streaming module (should be done once)
            import log_streaming
            log_streaming.initialize(account, log_streaming_config)
            if error:
                raise error

    @classmethod
    def setup(cls, env, yaml_file_name, log_level):
        Program.__setup_basic_logging(log_level)
        Program.__env = env

        with open(yaml_file_name) as y:
            Program.__yaml_config = yaml.load(y)

        Program.__setup_log_streaming()

    @classmethod
    def run(cls, eth_passphrase, eth_auth_token, sol_file):
        """
        Runs the backend
        """
        # Note: except for stream_logger, every other import
        # to a subpackage of qsp_prototol_node must be
        # performed at this point

        from audit import QSPAuditNode
        from config import ConfigFactory
        from utils.stop import Stop

        cfg = ConfigFactory.create_from_dictionary(
            Program.__yaml_config,
            Program.__env,
            account_passwd=eth_passphrase,
            auth_token=eth_auth_token,
        )

        logger.info("Initializing QSP Audit Node")
        logger.debug("account: {0}".format(cfg.account))
        logger.debug("analyzers: {0}".format(cfg.analyzers))
        logger.debug("audit contract address: {0}".format(cfg.audit_contract_address))

        logger.debug("min_price_in_qsp: {0}".format(cfg.min_price_in_qsp))
        logger.debug("evt_polling: {0}".format(cfg.evt_polling))

        # Based on the provided configuration, instantiates a new
        # QSP audit node
        audit_node = QSPAuditNode(cfg)
        Stop.register(audit_node)

        if QSPAuditNode.is_police_officer(cfg):
            logger.info("Running QSP node (performs audits and police checks)")
        else:
            logger.info("Running QSP node (performs audits only)")

        # If a sol file is given, produce the audit report for that file and exit
        if sol_file:
            _, audit_report = audit_node.get_full_report(
                requestor=cfg.account,
                uri=sol_file,
                request_id=1
            )
            pprint(audit_report)
        # Runs the QSP audit node in a busy loop fashion
        else:
            try:
                audit_node.start()
            except Exception as error:
                if audit_node is not None:
                    audit_node.stop()
                    raise error


if __name__ == "__main__":
    setup_exception = None
    logger = None
    try:

        Program.setup(
            os.environ['QSP_ENV'],
            os.environ['QSP_CONFIG'],
            os.environ['QSP_LOGGING_LEVEL']
        )
        sol_file = os.environ.get('SOL_FILE')
    except Exception as error:
        setup_exception = error

    try:
        from log_streaming import get_logger
        logger = get_logger(__name__)

        if setup_exception:
            raise setup_exception

        Program.run(os.environ['QSP_ETH_PASSPHRASE'], os.environ['QSP_ETH_AUTH_TOKEN'], sol_file)
    except Exception as error:
        if logger:
            logger.exception("Error in running node: {0}".format(str(error)))
        else:
            traceback.print_exc()
        exit(1)

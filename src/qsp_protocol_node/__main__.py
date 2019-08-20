####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################


# ***NOTE***
#
# ANY import to a module in the node's code base should
# be not occur here. Rather, make it local so that
# any declared logger is correctly routed to the LogStreamLogger
# Having a local import makes sure the logging in each imported
# module is correctly set (e.g., in case of having a global declared
# logger variable)

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


class Program:

    __yaml_config = None
    __env = None
    __account_passwd = None
    __version = None

    @classmethod
    def __expand_vars(cls, input_config, config_vars):
        """
        Expands variables referenced in a given config dictionary
        """

        # Check if there is something to expand
        if config_vars is None or len(config_vars) == 0:
            return input_config

        if type(input_config) is str:
            if "$" not in input_config:
                return input_config

            for var_name, var_value in config_vars.items():
                input_config = input_config.replace("${" + var_name + "}", var_value)

        elif type(input_config) is dict:
            new_dict = {}
            for key, value in input_config.items():
                new_dict[key] = Program.__expand_vars(value, config_vars)
            return new_dict

        elif type(input_config) is list:
            new_list = []
            for value in input_config:
                new_list.append(Program.__expand_vars(value, config_vars))
            return new_list

        return input_config

    @classmethod
    def __setup_basic_logging(cls, qsp_home_dir, level):
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
                    'filename': '{0}/qsp-protocol.log'.format(qsp_home_dir),
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
        keystore_file = get(Program.__yaml_config[Program.__env], "/keystore_file")

        with open(keystore_file) as k:
            keystore = load(k)

        # Get account
        account = Web3.toChecksumAddress('0x' + keystore['address'])

        # Get log streaming config (if any)
        log_streaming_config = None
        try:
            log_streaming_config = get(Program.__yaml_config[Program.__env], "/logging/streaming")
        except KeyError:
            pass

        # Initialize the log streaming module (should be done once)
        import log_streaming
        log_streaming.initialize(account, log_streaming_config)

    @classmethod
    def setup(cls, env, yaml_file_name, qsp_home_dir, version, auth_token, account_passwd, log_level):
        Program.__setup_basic_logging(qsp_home_dir, log_level)
        Program.__env = env
        Program.__account_passwd = account_passwd

        major_version = version[0:version.index('.')]
        config_vars = {
            'qsp-home': qsp_home_dir,
            'auth-token': auth_token,
            'major-version': major_version
        }

        with open(yaml_file_name) as y:
            Program.__yaml_config = Program.__expand_vars(yaml.load(y), config_vars)

        Program.__setup_log_streaming()

    @classmethod
    def load_config(cls):
        from config import ConfigFactory

        return ConfigFactory.create_from_dictionary(
            Program.__yaml_config,
            Program.__env,
            Program.__version,
            Program.__account_passwd
        )

    @classmethod
    def run_file(cls, config, sol_file):
        from audit import PerformAuditThread

        audit_thread = PerformAuditThread(config)
        _, audit_report = audit_thread.get_full_report(
                requestor=config.account,
                uri=sol_file,
                request_id=1
            )
        pprint(audit_report)

    @classmethod
    def run(cls, config):
        """
        Runs the backend
        """
        # Note: except for stream_logger, every other import
        # to a subpackage of qsp_prototol_node must be
        # performed at this point

        from audit import QSPAuditNode
        from utils.stop import Stop

        logger.info("Initializing QSP Audit Node")
        logger.debug("account: {0}".format(config.account))
        logger.debug("analyzers: {0}".format(config.analyzers))
        logger.debug("audit contract address: {0}".format(config.audit_contract_address))

        logger.debug("min_price_in_qsp: {0}".format(config.min_price_in_qsp))
        logger.debug("evt_polling: {0}".format(config.evt_polling))
        logger.debug("audit contract address: {0}".format(config.audit_contract_address))

        # Based on the provided configuration, instantiates a new
        # QSP audit node
        audit_node = QSPAuditNode(config)
        Stop.register(audit_node)

        if QSPAuditNode.is_police_officer(config):
            logger.info("Running QSP node (performs audits and police checks)")
        else:
            logger.info("Running QSP node (performs audits only)")

        try:
            audit_node.start()
        except Exception as error:
            if audit_node is not None:
                audit_node.stop()
                raise error


if __name__ == "__main__":
    logger = None
    try:
        Program.setup(
            os.environ['QSP_ENV'],
            os.environ['QSP_CONFIG'],
            os.environ['QSP_HOME'],
            os.environ['QSP_NODE_VERSION'],
            os.environ['QSP_ETH_AUTH_TOKEN'],
            os.environ['QSP_ETH_PASSPHRASE'],
            os.environ['QSP_LOGGING_LEVEL']
        )

        from log_streaming import get_logger
        logger = get_logger(__name__)

        sol_file = os.environ.get('SOL_FILE')
        config = Program.load_config()

        if sol_file is not None:
            Program.run_file(config, sol_file)
        else:
            Program.run(config)

    except Exception as error:
        if logger is not None:
            logger.exception("Error in running node: {0}".format(str(error)))
        else:
            traceback.print_exc()

        # A non-zero exit code is required to auto-restart
        exit(1)

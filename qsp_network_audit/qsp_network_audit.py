"""
Provides the main entry for executing a QSP audit node.
"""
import argparse
import signal
import traceback, sys
import utils.logging as logging_utils

import logging
logger = logging_utils.get_logger()

from audit import QSPAuditNode
from config import Config
from tendo.singleton import SingleInstance

import faulthandler
faulthandler.enable()

done = False
audit_node = None

def stop_audit_node():
    global done
    global audit_node

    if audit_node is None or done:
        return

    logging.info("Stopping QSP Audit Node")

    audit_node.stop()
    done = True

def configure_logging(verbose_level):
    logging_utils.config_logging(verbose_level)

    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)

def handle_stop_signal(signal, frame):
    stop_audit_node()

signal.signal(signal.SIGTERM, handle_stop_signal)
signal.signal(signal.SIGINT, handle_stop_signal)

def main():
    """
    Main function.
    """
    global audit_node
    try:
        # Sets the program's arguments
        parser = argparse.ArgumentParser(description='QSP Audit Node')

        parser.add_argument(
            'environment',
            metavar='environment', type=str,
            help='target environment to execute'
        )
        parser.add_argument(
            'config_yaml',
            metavar='config-yaml', type=str,
            help='yaml configuration file path'
        )
        parser.add_argument(
            '-p', '--password',
            type=str, default='',
            help='password for unlocking wallet account',
        )
        parser.add_argument(
            "-v", "--verbose",
            help="increase output verbosity",
            action="store_true",
            default=False,
        )

        # Validates input arguments
        args = parser.parse_args()

        configure_logging(args.verbose)

        # Creates a config object based on the provided environment
        # and configuration (given as a yaml file)
        cfg = Config(args.environment, args.config_yaml, args.password)

        logging.info("Initializing QSP Audit Node")
        logging.debug("account: {0}".format(str(cfg.account)))
        logging.debug("internal contract: {0}".format(
            str(cfg.internal_contract)))
        logging.debug("analyzer: {0}".format(str(cfg.analyzer)))
        logging.debug("min_price: {0}".format(str(cfg.min_price)))
        logging.debug("evt_polling: {0}".format(str(cfg.evt_polling)))

        # Based on the provided configuration, instantiates a new
        # QSP audit node
        audit_node = QSPAuditNode(cfg)

        logging.info("Running QSP audit node")

        # Runs the QSP audit node in a busy loop fashion
        audit_node.run()
    except Exception as error:
        logging.exception(
            "Cannot start audit node. {0}".format(
                str(error)
            )
        )
        traceback.print_exc(file=sys.stdout)
    finally:
        stop_audit_node()


if __name__ == "__main__":
    main()

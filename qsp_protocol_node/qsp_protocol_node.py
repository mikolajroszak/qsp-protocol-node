"""
Provides the main entry for executing a QSP audit node.
"""
import argparse
import signal
import traceback
import sys
import faulthandler

from audit import QSPAuditNode
from config import Config

faulthandler.enable()


def main():
    """
    Main function.
    """
    cfg = None
    audit_node = None
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

        # Validates input arguments
        args = parser.parse_args()

        # Creates a config object based on the provided environment
        # and configuration (given as a yaml file)
        cfg = Config(args.environment, args.config_yaml, args.password)

        cfg.logger.info("Initializing QSP Audit Node")
        cfg.logger.debug("account: {0}".format(str(cfg.account)))
        # todo(mderka): The reference cfg.audit_contract does not seem to exist
        cfg.logger.debug("audit contract: {0}".format(str(cfg.audit_contract)))
        cfg.logger.debug("analyzer: {0}".format(str(cfg.analyzer)))
        cfg.logger.debug("min_price: {0}".format(str(cfg.min_price)))
        cfg.logger.debug("evt_polling: {0}".format(str(cfg.evt_polling)))

        # Based on the provided configuration, instantiates a new
        # QSP audit node
        audit_node = QSPAuditNode(cfg)

        def handle_stop_signal(stop_signal, frame):
            audit_node.stop()

        signal.signal(signal.SIGTERM, handle_stop_signal)
        signal.signal(signal.SIGINT, handle_stop_signal)

        cfg.logger.info("Running QSP audit node")

        # Runs the QSP audit node in a busy loop fashion
        audit_node.run()
    except Exception as error:
        message = "Cannot start audit node. {0}".format(str(error))
        if cfg is not None:
            cfg.logger.exception(message)
        else:
            print(message, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        if audit_node is not None:
            audit_node.stop()


if __name__ == "__main__":
    main()

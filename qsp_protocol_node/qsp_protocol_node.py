"""
Provides the main entry for executing a QSP audit node.
"""
import argparse
import signal
import traceback
import sys

from audit import QSPAuditNode
from config import ConfigFactory
from stop import Stop


def main():
    """
    Main function.
    """

    ERR_EXCEPTION = 1
    ERR_INVALID_ARGUMENT = 2

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
            '-t', '--auth-token',
            type=str, default='',
            help='token for accessing the geth endpoint',
        )

        # Validates input arguments
        args = parser.parse_args()

    except SystemExit:
        Stop.error(code=ERR_INVALID_ARGUMENT)

    try:
        # Creates a config object based on the provided environment
        # and configuration (given as a yaml file)
        cfg = ConfigFactory.create_from_file(args.environment, args.config_yaml, args.password, args.auth_token)

        cfg.logger.info("Initializing QSP Audit Node")
        cfg.logger.debug("account: {0}".format(str(cfg.account)))
        cfg.logger.debug("analyzers: {0}".format(str(cfg.analyzers)))
        cfg.logger.debug("audit contract address: {0}".format(str(cfg.audit_contract_address)))
        cfg.logger.debug("analyzers: {0}".format(str(cfg.analyzers)))

        cfg.logger.debug("min_price: {0}".format(str(cfg.min_price)))
        cfg.logger.debug("evt_polling: {0}".format(str(cfg.evt_polling)))

        # Based on the provided configuration, instantiates a new
        # QSP audit node
        audit_node = QSPAuditNode(cfg)

        Stop.set_logger(cfg.logger)
        Stop.register(audit_node)

        cfg.logger.info("Running QSP audit node")

        # Runs the QSP audit node in a busy loop fashion
        audit_node.run()

    except Exception as error:
        # Useful for debugging. Enable the following
        # two commented lines

        # import sys, traceback
        # traceback.print_exc(file=sys.stdout)

        Stop.error(err=error, code=ERR_EXCEPTION)


if __name__ == "__main__":
    main()

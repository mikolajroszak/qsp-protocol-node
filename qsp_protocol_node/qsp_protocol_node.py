"""
Provides the main entry for executing a QSP audit node.
"""
import argparse
import signal
import traceback
import sys
from audit import QSPAuditNode
from config import ConfigFactory


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
        cfg = ConfigFactory.create_from_file(args.environment, args.config_yaml, args.password)

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

        def handle_stop_signal(signal, frame):
            # If not already stopping, stop.
            if not handle_stop_signal.stopping:
                handle_stop_signal.stopping = True
                audit_node.stop()

        handle_stop_signal.stopping = False

        signal.signal(signal.SIGTERM, handle_stop_signal)
        signal.signal(signal.SIGINT, handle_stop_signal)

        cfg.logger.info("Running QSP audit node")

        # Runs the QSP audit node in a busy loop fashion
        audit_node.run()

    except Exception as error:
        if audit_node is not None:
            audit_node.stop()

        error_msg = "Cannot start audit node. {0}".format(str(error))

        # Makes sure the initialization of the logger object is in place
        if cfg is not None and cfg.logger is not None:
            cfg.logger.exception(error_msg)
        else:
            # If not, just print to standard error
            print(error_msg, file=sys.stderr)

        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()

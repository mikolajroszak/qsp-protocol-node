"""
Provides the main entry for executing a QSP audit node.
"""
import argparse
import logging

from audit import QSPAuditNode
from config import Config

def config_logging(verbose):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.ERROR,
        format='%(levelname)s[%(threadName)s] %(message)s',
    )

def main():
    """
    Main function.
    """
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
            
        config_logging(args.verbose)

        # Creates a config object based on the provided environment
        # and configuration (given as a yaml file)
        cfg = Config(args.environment, args.config_yaml, args.password)

        logging.info("Initializing QSP Audit Node")

        # Based on the provided configuration, instantiates a new
        # QSP audit node
        audit_node = QSPAuditNode(
            cfg.web3_client.eth.accounts[cfg.account_id],
            cfg.internal_contract, 
            cfg.analyzer,
            cfg.min_price,
            cfg.evt_polling,
            cfg.analyzer_output,
        )

        logging.info("Running QSP audit node")

        # Runs the QSP audit node in a busy loop fashion
        audit_node.run()
    except Exception:
        logging.exception("Unexpected error")
        

if __name__ == "__main__":
    main()

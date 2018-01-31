"""
Provides the main entry for executing a QSP audit node.
"""
import argparse
import traceback
import sys

from audit import QSPAuditNode
from config import Config

def main():
    """
    Main function.
    """
    verbose = False
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
            "-v", "--verbose", 
            help="increase output verbosity",
            action="store_true" 
        )

        # Validates input arguments
        args = parser.parse_args()
        verbose = args.verbose

        # Creates a config object based on the provided environment
        # and configuration (given as a yaml file)
        cfg = Config(args.environment, args.config_yaml)

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

        # Runs the QSP audit node in a busy loop fashion
        audit_node.run()
    except Exception as e:
        if verbose:
            traceback.print_exc()
        else:
            print(str(e), sys.stderr) 
        

if __name__ == "__main__":
    main()

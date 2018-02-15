"""
Provides an interface for invoking the analyzer software.
"""

import subprocess
import os
import logging

from utils.io import load_json, has_matching_line
from utils.args import replace_args
from solc import compile_files, ContractsNotFound, SolcError


class Analyzer:

    def __init__(self, cmd_template, locked_version):
        """
        Builds an Analyzer object from a given command template and supported version of
        the Solidity language.
        """
        self.__cmd_template = cmd_template
        self.__locked_version = locked_version

    def __supports_target_solidity_version(self, contract):
        """
        Verifies whether the target Solidity version in a contract is supported or not.
        """
        pragma_regex = "^pragma\\s+solidity\\s+\^?{0}\\s*;\\s*$".format(
            self.__locked_version.replace('.', '\\.')
        )

        return has_matching_line(contract, pragma_regex)

    def __create_err_result(self, msg):
        return {
            'status': 'error',
            'result': {
                'message': msg
            },
        }

    def __create_succ_result(self, report):
        return {
            'status': 'success',
            'result': report,
        }

    def check(self, contract, output_name_template):
        """
        Checks for potential vulnerabilities in a target contract writen in a given
        version of Solidity, writing the corresponding results in the provided output.
        """
        try:
            if not self.__supports_target_solidity_version(contract):
                raise Exception(
                    "Solidity version in target contract does not match locked one ({0})".format(
                        self.__locked_version,
                    )
                )

            # Attempts to compile the target contract. If it fails, a ContractsNotFound
            # exception is thrown
            compile_files([contract])

            injected_output = replace_args(output_name_template,
                                           {"${input}": contract}
                                           )
            injected_cmd = replace_args(self.__cmd_template, {
                "${input}": contract,
                "${solidity_version}": self.__locked_version,
                "${output}": injected_output,
            })

            logging.debug("Executing check on contract {0}".format(contract))
            logging.debug("Output set to {0}".format(injected_output))
            logging.debug("Analyzer command set to {0}".format(injected_cmd))

            # NOTE: in some occasions, oyenete sucessfully runs, but
            # still returns a non-zero status. Consequently, 'check'
            # has to be set to False.
            # See issue: https://github.com/quantstamp/qsp-analyzer-oyente/issues/2

            # The only way to assure whether an error occurred is if the expected file
            # was not created, or if so, if it is empty. In either case, remove the
            # output file.
            if os.path.isfile(injected_output):
                os.remove(injected_output)

            logging.debug("Invoking analyzer tool as a subprocess")

            # TODO Add timeout parameter based on a configuration parameter
            subprocess.run(injected_cmd, shell=True)

            logging.debug("Done running analyzer process")

            if os.path.isfile(injected_output):

                logging.debug(
                    "Loading result from {0}".format(injected_output))

                result = load_json(injected_output)

                os.remove(injected_output)

                if result is not None and result:
                    logging.debug("Analysis result is {0}".format(str(result)))
                    return self.__create_succ_result(result)

            # Unknown error. Report it as such
            raise Exception("Failed in running analyzer. Skipping...")

        except ContractNotFound as error:
            return self.__create_err_result(str(error.stderr_data))

        except SolcError as error:
            return self.__create_err_result(str(error.stderr_data))

        except Exception as error:
            return self.__create_err_result(str(error))

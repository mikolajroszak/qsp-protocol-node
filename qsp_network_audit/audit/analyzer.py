"""
Provides an interface for invoking the analyzer software.
"""

import subprocess
import os
from utils.io import load_json, has_matching_line

class Analyzer:

    def __init__(self, cmd_template, locked_version):
        """
        Builds an Analyzer object from a given command template and supported version of
        the Solidity language.
        """
        self.__cmd_template = cmd_template
        self.__locked_version = locked_version
    
    def __inject_args(self, entry, input_args):
        """
        Injects a set of input arguments into the command template, returning a 
        command instance.
        """
        for name in input_args:
            entry = entry.replace(name, input_args[name])
        return entry     
    
    def __supports_target_solidity_version(self, contract):
        """
        Verifies whether the target Solidity version in a contract is supported or not.
        """
        pragma_regex = "^pragma\\s+solidity\\s+\^?{0}\\s*;\\s*$".format(
            self.__locked_version.replace('.', '\\.')
        )

        return has_matching_line(contract, pragma_regex)

    def check(self, contract, output):
        """
        Checks for potential vulnerabilities in a target contract writen in a given 
        version of Solidity, writing the corresponding results in the provided output.
        """
        if not self.__supports_target_solidity_version(contract):
            raise Exception(
                "Solidity version in target contract does not match locked one ({0})".format(
                    self.__locked_version,
                )
            )

        output_args = { "${input}": contract}
        injected_output = self.__inject_args(output, output_args)

        cmd_args = {
            "${input}": contract,
            "${solidity_version}": self.__locked_version,
            "${output}": output,
        }
        injected_cmd = self.__inject_args(self.__cmd_template, cmd_args)

        # NOTE: in some occasions, oyenete sucessfully runs, but
        # still returns a non-zero status. Consequently, 'check'
        # has to be set to False.
        # See issue: https://github.com/quantstamp/qsp-analyzer-oyente/issues/2

        # The only way to assure whether an error occurred is if the expected file
        # was not created, or if so, if it is empty. In either case, remove the
        # output file.
        if os.path.isfile(injected_output):
            os.remove(injected_output)

        analyzer_tool = subprocess.run(injected_cmd, shell=True)

        if os.path.isfile(injected_output):
            result = load_json(injected_output)
            os.remove(injected_output)

            if result is not None and result:
                return result
        
        raise Exception("Failed in running analyzer. Skipping...")

        




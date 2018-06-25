"""
Provides an interface for invoking the analyzer software.
"""

import json

from utils.io import digest


class AnalyzerRunException(Exception):
    def __init__(self, message, output):
        self.__message = message
        self.__output = output

    @property
    def message(self):
        return self.__message

    @property
    def output(self):
        return self.__output


class Analyzer:

    def __init__(self, wrapper, logger):
        """
        Builds an Analyzer object from a given arguments string.
        """
        self.__wrapper = wrapper
        self.__logger = logger

    @property
    def wrapper(self):
        return self.__wrapper

    def check(self, contract_path, request_id):
        """
        Checks for potential vulnerabilities in a target contract writen in a given
        version of Solidity, writing the result in a json report.
        """
        self.__logger.debug("Running {0}'s wrapper. About to check {1}".format(
                self.__wrapper.analyzer_name, contract_path
            ),
            requestId=request_id,
        )

        json_report = self.__wrapper.check(contract_path, request_id)
        str_report = json.dumps(json_report)
        json_report['hash'] = digest(str_report)

        self.__logger.debug("{0}'s wrapper finished execution. Produced report is {1}".format(
                self.__wrapper.analyzer_name,
                str_report,
            ),
            requestId=request_id,
        )

        return json_report

        # TODO
        # One must make sure there is no compilation error prior to calling any analyzer.
        # This logic shall be lifted to the audit node level
        # See QSP-416
        # https://quantstamp.atlassian.net/browse/QSP-416

        # try:

        #     # Attempts to compile the target contract. If it fails, a ContractsNotFound
        #     # exception is thrown
        #     compile_files([contract])

        #     injected_output = replace_args(output_name_template,
        #                                    {"${input}": contract}
        #                                    )
        #     injected_cmd = replace_args(self.__cmd_template, {
        #         "${input}": contract,
        #         "${output}": injected_output,
        #     })

        #     self.__logger.debug("Executing check on contract {0}".format(contract),
        #                         requestId=request_id)
        #     self.__logger.debug("Output set to {0}".format(injected_output), requestId=request_id)
        #     self.__logger.debug("Analyzer command set to {0}".format(injected_cmd),
        #                         requestId=request_id)

        #     # NOTE: in some occasions, oyente successfully runs, but
        #     # still returns a non-zero status. Consequently, 'check'
        #     # has to be set to False.
        #     # See issue: https://github.com/quantstamp/qsp-analyzer-oyente/issues/2

        #     # The only way to assure whether an error occurred is if the expected output file
        #     # was not created, or if so, if it is empty. In either case, remove the
        #     # output file.
        #     if os.path.isfile(injected_output):
        #         os.remove(injected_output)

        #     self.__logger.debug("Invoking analyzer tool as a subprocess", requestId=request_id)

        #     # TODO Add timeout parameter based on a configuration parameter
        #     analyzer_result = subprocess.run(injected_cmd, shell=True, stdout=subprocess.PIPE,
        #                                      stderr=subprocess.STDOUT)

        #     self.__logger.debug("Done running analyzer process", requestId=request_id)
        #     self.__logger.debug("Analyzer output: {0}".format(analyzer_result.stderr),
        #                         requestId=request_id)

        #     if os.path.isfile(injected_output):
        #         self.__logger.debug(
        #             "Loading result from {0}".format(injected_output), requestId=request_id)

        #         result = load_json(injected_output)
        #         os.remove(injected_output)

        #         if result is not None and result:
        #             self.__logger.debug("Analysis result is {0}".format(str(result)),
        #                                 requestId=request_id)
        #             return self.__create_succ_result(result)

        #     # Unknown error. Report it as such
        #     raise AnalyzerRunException("Failed in running analyzer", analyzer_result.stdout)

        # except ContractsNotFound as error:
        #     self.__logger.debug("Error calling analyzer: {0}".format(str(error)),
        #                         requestId=request_id)
        #     return self.__create_err_result(str(error.stderr_data))

        # except SolcError as error:
        #     self.__logger.debug("Error calling analyzer: {0}".format(str(error)),
        #                         requestId=request_id)
        #     return self.__create_err_result(str(error.stderr_data))

        # except AnalyzerRunException as error:
        #     self.__logger.debug("Error calling analyzer: {0}".format(str(error)),
        #                         requestId=request_id)
        #     return self.__create_err_result(str(error.output))

        # except Exception as error:
        #     self.__logger.debug("Error calling analyzer: {0}".format(str(error)),
        #                         requestId=request_id)
        #     return self.__create_err_result(str(error))

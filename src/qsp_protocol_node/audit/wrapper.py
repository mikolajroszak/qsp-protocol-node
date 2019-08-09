####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################

import json
import os
import subprocess

from utils.io import (
    dir_exists,
    file_exists,
    is_executable,
)
from log_streaming import get_logger


class Wrapper:

    @staticmethod
    def __check_for_executable_script(script):
        file_exists(script, throw_exception=True)
        is_executable(script, throw_exception=True)

    def __init__(self, wrappers_dir, analyzer_name, args, storage_dir, timeout_sec, prefetch=True):
        self.__logger = get_logger(self.__class__.__qualname__)
        self.__analyzer_name = analyzer_name

        self.__home = "{0}/{1}".format(wrappers_dir, analyzer_name)
        self.__args = args

        if not dir_exists(storage_dir):
            os.makedirs(storage_dir)

        self.__storage_dir = storage_dir
        self.__timeout_sec = timeout_sec

        metadata_script = "{0}/metadata".format(self.home)
        run_script = "{0}/run".format(self.home)
        pull_script = "{0}/pull_analyzer".format(self.home)
        Wrapper.__check_for_executable_script(run_script)
        Wrapper.__check_for_executable_script(metadata_script)
        Wrapper.__check_for_executable_script(pull_script)

        self.__metadata_script = metadata_script
        self.__run_script = run_script
        self.__pull_script = pull_script

        # Prefetch the configured analyzer image. If the prefetching fails,
        # an exception is thrown, the program exits and the auto-restart feature kicks in.
        if prefetch:
            self.__pull_analyzer()

    @property
    def analyzer_name(self):
        return self.__analyzer_name

    @property
    def home(self):
        return self.__home

    @property
    def args(self):
        return self.__args

    @property
    def storage_dir(self):
        return self.__storage_dir

    @property
    def timeout_sec(self):
        return self.__timeout_sec

    def get_base_environment(self):
        env_vars = os.environ.copy()

        env_vars['STORAGE_DIR'] = self.__storage_dir
        env_vars['WRAPPER_HOME'] = self.__home
        env_vars['ANALYZER_NAME'] = self.__analyzer_name
        env_vars['ANALYZER_ARGS'] = self.__args
        return env_vars

    def get_full_environment(self, contract_path, original_file_name):
        env_vars = self.get_base_environment()
        contract_file_name = os.path.basename(contract_path)

        env_vars['CONTRACT_PATH'] = contract_path
        env_vars['CONTRACT_FILE_NAME'] = contract_file_name
        env_vars['ORIGINAL_FILE_NAME'] = original_file_name
        return env_vars

    def get_metadata(self, contract_path, request_id, original_file_name):
        metadata = {'name': self.__analyzer_name}
        try:
            env_vars = self.get_full_environment(contract_path, original_file_name)
            self.__logger.debug(
                "Getting {0}'s metadata as subprocess".format(self.analyzer_name),
                requestId=request_id,
            )

            analyzer = subprocess.run(
                self.__metadata_script,
                env=env_vars,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=self.__timeout_sec,
                cwd=self.__home,
            )

            metadata = json.loads(analyzer.stdout)

        except Exception as inner_error:
            self.__logger.error("Error collecting the metadata from {0}'s wrapper: {1}".format(
                    self.analyzer_name,
                    str(inner_error),
                ),
                requestId=request_id
            )

        return metadata

    def __pull_analyzer(self):
        try:
            env_vars = self.get_base_environment()
            self.__logger.debug(
                "Prefetching {0} image".format(self.analyzer_name)
            )

            subprocess.run(
                self.__pull_script,
                env=env_vars,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=self.__timeout_sec,
                cwd=self.__home,
            )
        except subprocess.CalledProcessError as inner_error:
            msg = "Downloading image for {0}'s wrapper ended with non-zero status: {1}"
            self.__logger.error(msg.format(self.analyzer_name, str(inner_error)))
            raise inner_error
        except Exception as inner_error:
            self.__logger.error("Error downloading image for {0}'s wrapper: {1}".format(
                    self.analyzer_name,
                    str(inner_error),
                )
            )
            raise inner_error

    def check(self, contract_path, request_id, original_file_name):
        json_report = {}
        try:
            env_vars = self.get_full_environment(contract_path, original_file_name)
            self.__logger.debug("Invoking {0}'s wrapper as subprocess".format(
                    self.analyzer_name
                ),
                requestId=request_id,
            )

            analyzer = subprocess.run(
                self.__run_script,
                env=env_vars,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=self.__timeout_sec,
                cwd=self.__home,
            )

            self.__logger.debug("Wrapper stdout is: {0}".format(str(analyzer.stdout)),
                                requestId=request_id)
            self.__logger.debug("Wrapper stderr is: {0}".format(str(analyzer.stderr)),
                                requestId=request_id)

            json_report = json.loads(analyzer.stdout)

        except subprocess.TimeoutExpired as err:
            self.__logger.debug("Timeout running {0}'s wrapper: {1}".format(
                self.analyzer_name,
                str(err),
            ),
                requestId=request_id
            )
            # Cannot produce result in time. Get this back to the callee.
            raise err

        except Exception as err:
            self.__logger.error("Error running {0}'s wrapper: {1}".format(
                    self.analyzer_name,
                    str(err),
                ),
                requestId=request_id
            )
            # Cannot produce result. Get this back to the callee.
            raise err

        return json_report

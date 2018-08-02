from utils.io import (
    dir_exists,
    file_exists,
    is_executable,
)

import calendar
import json
import os
import subprocess
import time


class Wrapper:

    @staticmethod
    def __check_for_executable_script(script):
        file_exists(script, throw_exception=True)
        is_executable(script, throw_exception=True)

    def __init__(self, wrappers_dir, analyzer_name, args, storage_dir, timeout_sec, logger):
        self.__analyzer_name = analyzer_name

        self.__home = "{0}/{1}".format(wrappers_dir, analyzer_name)
        self.__args = args

        if not dir_exists(storage_dir):
            os.makedirs(storage_dir)

        self.__storage_dir = storage_dir

        self.__timeout_sec = timeout_sec

        metadata_script = "{0}/get_metadata".format(self.home)
        run_script = "{0}/run".format(self.home)
        Wrapper.__check_for_executable_script(run_script)
        Wrapper.__check_for_executable_script(metadata_script)

        self.__metadata_script = metadata_script
        self.__run_script = run_script
        # print("RUN WRAPPER: " + str(run_script))
        self.__logger = logger

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

    def setup_environment(self, contract_path, original_file_name):
        env_vars = os.environ.copy()
        env_vars['STORAGE_DIR'] = self.__storage_dir

        env_vars['WRAPPER_HOME'] = self.__home
        env_vars['ANALYZER_NAME'] = self.__analyzer_name
        env_vars['CONTRACT_PATH'] = contract_path
        env_vars['ORIGINAL_NAME'] = original_file_name
        env_vars['ANALYZER_ARGS'] = self.__args
        return env_vars

    @staticmethod
    def process_metadata(metadata_str):
        """
        Assumes the following input:
        name
        version
        command
        list of vulnerabilities (one per line)
        """
        lines = metadata_str.split("\n")
        metadata = {}
        metadata['name'] = lines[0]
        metadata['version'] = lines[1]
        metadata['command'] = lines[2]
        vulnerability_list = lines[3:]
        metadata['vulnerabilities_checked'] = [v for v in vulnerability_list if v != ""]
        return {'analyzer': metadata}

    def get_metadata(self, contract_path, request_id, original_file_name):
        try:
            env_vars = self.setup_environment(contract_path, original_file_name)
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
            )
            return Wrapper.process_metadata(analyzer.stdout)

        except Exception as inner_error:
            json_report = {
                'analyzer': {'name': self.__analyzer_name}
            }
            self.__logger.error("Error collecting the metadata from {0}'s wrapper: {1}".format(
                    self.analyzer_name,
                    str(inner_error),
                ),
                requestId=request_id
            )

        return json_report

    def check(self, contract_path, request_id, original_file_name):
        analyzer = None
        start_time = None
        end_time = None
        error = False
        try:
            env_vars = self.setup_environment(contract_path, original_file_name)
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
            )
            json_report = json.loads(analyzer.stdout)

        except Exception as inner_error:
            # This should never occur; the wrapper should never
            # throw an exception, i.e., if an error occurs it should
            # be wrapped according to the integration schema.

            # But, for whatever reason an error does occur (e.g.,
            # subprocess fails creating a new analyzer thread),
            # then produce a minimal report with whatever information
            # is known at this point.
            error = True
            json_report = {
                'analyzer': {'name': self.__analyzer_name},
                'status': 'error',
                'errors': [str(inner_error)],
            }

            self.__logger.error("Error running {0}'s wrapper: {1}".format(
                    self.analyzer_name,
                    str(inner_error),
                ),
                requestId=request_id
            )

        if analyzer is not None:
            self.__logger.debug("Wrapper stdout is: {0}".format(str(analyzer.stdout)), requestId=request_id)
            self.__logger.debug("Wrapper stderr is: {0}".format(str(analyzer.stderr)), requestId=request_id)

        if start_time is not None:
            json_report['start_time'] = start_time

        if end_time is not None:
            json_report['end_time'] = end_time

        if not error:
            self.__logger.debug("{0}'s wrapper successfully executed".format(self.analyzer_name))

        return json_report

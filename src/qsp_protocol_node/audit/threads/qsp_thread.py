####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from time import sleep, time

from log_streaming import get_logger


class QSPThread:
    """
    A class that all threads inside of the audit node should inherit from.
    """
    # Determines how long threads will sleep between waking up to react to events
    __THREAD_SLEEP_TIME = 0.1

    def __init__(self, config):
        """
        Builds an abstract thread object from the given input parameters.
        """
        self.__logger = get_logger(self.__class__.__qualname__)
        self.__config = config
        self.__exec = False

    def run_with_interval(self, body_function, polling_interval, start_with_call=True):
        """
        Periodically executes the function with a given interval.
        """
        self.__exec = True
        last_called = 0
        if not start_with_call:
            last_called = time()
        while self.__exec:
            now = time()
            if now - last_called > polling_interval:
                body_function()
                last_called = now
            sleep(QSPThread.__THREAD_SLEEP_TIME)

    def run_when_block_mined(self, body_function):
        """
        Checks if a new block is mined. Reacting to a new block the handler is called.
        """
        self.__exec = True

        current_block = 0
        last_called = 0
        while self.__exec:
            now = time()
            if now - last_called > self.__config.block_mined_polling:
                last_called = now
                if current_block < self.__config.web3_client.eth.blockNumber:
                    current_block = self.__config.web3_client.eth.blockNumber
                    self.__logger.debug("A new block is mined # {0}".format(str(current_block)))
                    try:
                        body_function()
                    except Exception as e:
                        self.__logger.exception(
                            "Error in block mined thread handler: {0}".format(str(e)))
                        raise e
            sleep(QSPThread.__THREAD_SLEEP_TIME)

    @property
    def thread_name(self):
        return self.__class__.__qualname__

    @property
    def config(self):
        return self.__config

    @property
    def logger(self):
        return self.__logger

    @property
    def exec(self):
        return self.__exec

    def start(self):
        """
        Starts the main function for this thread. This function is to be overriden by every
        implementation.
        """
        self.__exec = True

    def stop(self):
        """
        Signals to the thread that the execution of the internal function loop should be stopped.
        """
        self.__exec = False

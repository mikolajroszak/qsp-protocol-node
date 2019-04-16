####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

from abc import ABC, abstractmethod
from time import sleep
from time import time
from threading import Thread

from log_streaming import get_logger


class QSPThread(Thread, ABC):
    """
    A class that all threads inside of the audit node should inherit from.
    """
    # Determines how long threads will sleep between waking up to react to events
    THREAD_SLEEP_TIME = 0.1

    def __init__(self, config, target_function, thread_name,
                 start_with_call=True):
        """
        Builds an abstract thread object from the given input parameters.
        """
        # No need to pass the target function as this point, as this
        # class is abstract by design. Instead, save the reference internally
        # to allow subclasses to invoke the target function when overriding
        # the run() method
        Thread.__init__(self, name=thread_name)

        # Private attributes not to be accessed directly, but
        # through their corresponding properties
        self.__logger = get_logger(self.__class__.__qualname__)
        self.__config = config

        # Protected attributes to be accessed by child subclasses only
        self._target_function = target_function
        self._start_with_call = start_with_call

        # Protected attributes to be accessed by child subclases and
        # whose state can be probed by others (i.e., there is a corresponding
        # property)
        self._exec = False

    @abstractmethod
    def run(self):
        pass

    def sleep_time(self):
        return QSPThread.THREAD_SLEEP_TIME

    @property
    def config(self):
        return self.__config

    @property
    def logger(self):
        return self.__logger

    @property
    def exec(self):
        return self._exec

    def stop(self):
        """
        Signals to the thread that the execution of the internal function loop should be stopped.
        """
        self._exec = False


class TimeIntervalPollingThread(QSPThread):

    def __init__(self, config, target_function, thread_name,
                 polling_interval=None, start_with_call=True):
        if polling_interval is None:
            polling_interval = config.evt_polling

        QSPThread.__init__(self, config, target_function, thread_name,
                           start_with_call)
        self.__polling_interval = polling_interval

    # This was previously named `run_with_interval`
    def run(self):
        """
        Periodically executes the function with a given interval.
        """
        self._exec = True
        last_called = 0
        if not self._start_with_call:
            last_called = time()
        while self._exec:
            now = time()
            if now - last_called > self.__polling_interval:
                self._target_function()
                last_called = now
            sleep(self.sleep_time())


class BlockMinedPollingThread(QSPThread):

    def __init__(self, config, target_function, thread_name,
                 start_with_call=True):
        QSPThread.__init__(self, config, target_function, thread_name,
                           start_with_call)

    # This was previously named `run_when_block_mined`
    def run(self):
        """
        Checks if a new block is mined. Reacting to a new block the handler is called.
        """
        self._exec = True
        current_block = 0
        last_called = 0
        while self._exec:
            now = time()
            if now - last_called > self.config.block_mined_polling:
                last_called = now
                if current_block < self.config.web3_client.eth.blockNumber:
                    current_block = self.config.web3_client.eth.blockNumber
                    try:
                        self._target_function(current_block)
                    except Exception as e:
                        self.__logger.exception(
                            "Error in block mined thread handler: {0}".format(str(e)))
                        raise e
            sleep(self.sleep_time())

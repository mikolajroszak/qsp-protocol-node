####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
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

    def __init__(self, config):
        QSPThread.__init__(self, config, None, "block_mined_polling thread", False)
        self.current_block = 0

    # This was previously named `run_when_block_mined`
    def run(self):
        """
        Checks if a new block is mined. Reacting to a new block the handler is called.
        """
        self._exec = True
        last_called = 0
        while self._exec:
            now = time()
            if now - last_called > self.config.block_mined_polling:
                last_called = now
                remote_block_number = self.config.web3_client.eth.blockNumber
                if self.current_block < remote_block_number:
                    self.current_block = remote_block_number
            sleep(self.sleep_time())


class BlockMinedSubscriberThread(QSPThread):
    def __init__(self, config, target_function, thread_name, block_mined_polling_thread):
        QSPThread.__init__(self, config, target_function, thread_name, True)
        self.__block_mined_polling_thread = block_mined_polling_thread

    def run(self):
        """
        Checks if a new block is mined. Reacting to a new block the handler is called.
        """
        self._exec = True
        last_block_number = 0
        while self._exec:
            if last_block_number != self.__block_mined_polling_thread.current_block:
                last_block_number = self.__block_mined_polling_thread.current_block
                self._target_function(last_block_number)
            sleep(self.sleep_time())

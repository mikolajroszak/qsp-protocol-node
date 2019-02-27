####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import signal
import sys

from stream_logger import get_logger

logger = get_logger(__name__)


class Stop:
    """
    A class providing a stop notification mechanism for all registered
    stoppable objects (a stoppable object is one prodiving a stop
    function), as well as an exiting mechanism for the executing process to
    terminate altogether.
    """
    __objects = []

    @classmethod
    def stop_all(cls):
        """
        Stops all registered stoppable objects.
        """
        for stoppable in Stop.__objects:
            stoppable.stop()

    @classmethod
    def register(cls, stoppable):
        """
        Registers a stoppable object to be notified
        of stop-related events.
        """
        Stop.__objects.append(stoppable)

    @classmethod
    def objects(cls):
        """
        Returns the list of registered stoppable objects.
        """
        return Stop.__objects

    @classmethod
    def deregister(cls, stoppable):
        Stop.__objects.remove(stoppable)

    @classmethod
    def normal(cls):
        """
        Signals a normal stop. Stops all registered stoppable objects,
        exiting with status code 0.
        """
        Stop.stop_all()
        sys.exit(0)

    @classmethod
    def sigkill(cls):
        """
        Signals a KILL/TERM stop. Exits the process with a 0 status code.
        """
        sys.exit(0)

    @classmethod
    def error(cls, err=None, code=1):
        """
        Signals an error stop. Stops all registered stoppable objects,
        exiting with status code 1.
        """
        if code < 1:
            raise ValueError("Excepting error code >= 1, but found {0}".format(code))

        Stop.stop_all()
        if err is not None:
            logger.exception(err)
        sys.exit(code)


def __handle_sigkill_signal(signal, frame):
    """
    Handles SIGKILL/SIGTERM signals, stopping all
    registered stoppable objects.
    """
    if __handle_sigkill_signal.stopping:
        return

    __handle_sigkill_signal.stopping = True
    try:
        Stop.stop_all()
    except Exception as e:
        logger.exception(e)

    Stop.sigkill()


__handle_sigkill_signal.stopping = False

# Registers __handle_sigkill_signal as a handler for both
# SIGKILL/SIGTERM signals
signal.signal(signal.SIGTERM, __handle_sigkill_signal)
signal.signal(signal.SIGINT, __handle_sigkill_signal)

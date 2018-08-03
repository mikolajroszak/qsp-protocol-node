import signal
import sys


def print_err(logger, err):
    """
    Prints an error message to a given non-null logger or
    prints to stderr otherwise.
    """
    if logger is not None:
        logger.exception(str(err))
    else:
        # If not, just print to standard error
        print(str(err), file=sys.stderr)


class Stop:
    """
    A class providing a stop notification mechanism for all registered
    stoppable objects (a stoppable object is one prodiving a stop
    function), as well as an exiting mechanism for the executing process to
    terminate altogether.
    """
    __objects = []
    __logger = None

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
    def set_logger(cls, logger):
        """"
        Sets the logger for printing debug/error messages.
        """
        Stop.__logger = logger

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
            print_err(Stop.__logger, err)
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
        print_err(Stop.__logger, e)

    Stop.sigkill()


__handle_sigkill_signal.stopping = False

# Registers __handle_sigkill_signal as a handler for both
# SIGKILL/SIGTERM signals
signal.signal(signal.SIGTERM, __handle_sigkill_signal)
signal.signal(signal.SIGINT, __handle_sigkill_signal)

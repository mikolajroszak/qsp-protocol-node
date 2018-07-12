import unittest
import uuid

from helpers.function_call import FunctionCall
from stop import Stop
from stop import __handle_sigkill_signal as handle


class Stoppable:
    def __init__(self):
        self.__id = uuid.uuid4()
        self.__stopped = False

    def stop(self):
        self.__stopped = True

    @property
    def is_stopped(self):
        return self.__stopped

    @property
    def id(self):
        return self.__id


class MockSys:
    """
    A mock class used as stub for the internals of the Web3 provider.
    """

    def __init__(self):
        self.expected = []

    def expect(self, function_name, params, return_value):
        """
        Adds an expected function call to the queue.
        """
        self.expected.append(FunctionCall(function_name, params, return_value))

    def verify(self):
        """
        Verifies that all the expected calls were performed.
        """
        if len(self.expected) != 0:
            raise Exception('Some excpected calls were left over: ' + str(self.expected))

    def call(self, function_name, arguments_to_check, local_values):
        """
        Simulates call to the specified function while checking the expected parameter values
        """
        first_call = self.expected[0]
        if first_call.function_name != function_name:
            raise Exception('{0} call expected'.format(function_name))
        for argument in arguments_to_check:
            if first_call.params[argument] != local_values[argument]:
                msg = 'Value of {0} is not {1} as expected but {2}'
                raise Exception(
                    msg.format(argument, first_call.params[argument], local_values[argument]))
        self.expected = self.expected[1:]
        return first_call.return_value

    def exit(self, code):
        """
        A stub for the exit method.
        """
        arguments_to_check = ['code']
        return self.call('exit', arguments_to_check, locals())


class StopTest(unittest.TestCase):

    def setUp(self):
        Stop.__objects = []

    def test_register(self):
        number_of_registered_objects = len(Stop.objects())
        Stop.register(Stoppable())
        self.assertEqual(len(Stop.objects()), number_of_registered_objects + 1)

    def test_deregister(self):
        stoppable = Stoppable()
        Stop.register(stoppable)
        number_of_registered_objects = len(Stop.objects())
        Stop.deregister(stoppable)
        self.assertEqual(len(Stop.objects()), number_of_registered_objects - 1)

    def test_stop_all(self):
        stoppables = [
            Stoppable(),
            Stoppable(),
            Stoppable(),
            Stoppable()
        ]
        Stop.register(stoppables[0])
        Stop.register(stoppables[1])
        Stop.register(stoppables[2])
        Stop.register(stoppables[3])
        Stop.stop_all()

        self.assertTrue(stoppables[0].is_stopped)
        self.assertTrue(stoppables[1].is_stopped)
        self.assertTrue(stoppables[2].is_stopped)
        self.assertTrue(stoppables[3].is_stopped)

    def test_sigkill(self):
        original_sys = Stop._Stop__sys
        Stop._Stop__sys = MockSys()
        Stop._Stop__sys.expect('exit', {'code': 0}, None)
        Stop.sigkill()
        Stop._Stop__sys.verify()
        Stop._Stop__sys = original_sys

    def test_normal(self):
        original_sys = Stop._Stop__sys
        stoppables = [
            Stoppable(),
            Stoppable(),
            Stoppable(),
            Stoppable()
        ]
        Stop.register(stoppables[0])
        Stop.register(stoppables[1])
        Stop.register(stoppables[2])
        Stop.register(stoppables[3])
        Stop._Stop__sys = MockSys()
        Stop._Stop__sys.expect('exit', {'code': 0}, None)
        Stop.normal()
        Stop._Stop__sys.verify()
        self.assertTrue(stoppables[0].is_stopped)
        self.assertTrue(stoppables[1].is_stopped)
        self.assertTrue(stoppables[2].is_stopped)
        self.assertTrue(stoppables[3].is_stopped)
        Stop._Stop__sys = original_sys

    def test_set_logger(self):
        orioginal_logger = Stop._Stop__logger
        Stop.set_logger(15)
        self.assertEqual(15, Stop._Stop__logger)
        Stop._Stop__logger = orioginal_logger

    def test_error(self):
        original_sys = Stop._Stop__sys
        stoppables = [
            Stoppable(),
            Stoppable(),
            Stoppable(),
            Stoppable()
        ]
        Stop.register(stoppables[0])
        Stop.register(stoppables[1])
        Stop.register(stoppables[2])
        Stop.register(stoppables[3])
        Stop._Stop__sys = MockSys()
        error_code = 17
        Stop._Stop__sys.expect('exit', {'code': error_code}, None)
        Stop.error("Some error", error_code)
        Stop._Stop__sys.verify()
        self.assertTrue(stoppables[0].is_stopped)
        self.assertTrue(stoppables[1].is_stopped)
        self.assertTrue(stoppables[2].is_stopped)
        self.assertTrue(stoppables[3].is_stopped)
        Stop._Stop__sys = original_sys

    def test_handle_sigkill_signal(self):
        original_sys = Stop._Stop__sys
        stoppables = [
            Stoppable(),
            Stoppable(),
            Stoppable(),
            Stoppable()
        ]
        Stop.register(stoppables[0])
        Stop.register(stoppables[1])
        Stop.register(stoppables[2])
        Stop.register(stoppables[3])
        Stop._Stop__sys = MockSys()
        Stop._Stop__sys.expect('exit', {'code': 0}, None)
        handle(15, 0)
        self.assertTrue(handle.stopping)
        Stop._Stop__sys.verify()
        self.assertTrue(stoppables[0].is_stopped)
        self.assertTrue(stoppables[1].is_stopped)
        self.assertTrue(stoppables[2].is_stopped)
        self.assertTrue(stoppables[3].is_stopped)
        # this should just return now
        self.assertIsNone(handle(15, 0))
        Stop._Stop__sys.verify()
        Stop._Stop__sys = original_sys
        handle.stopping = False

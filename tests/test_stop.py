####################################################################################################
#                                                                                                  #
# (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,          #
# modified, redistributed, or otherwise disseminated except to the extent expressly authorized by  #
# Quantstamp for credentialed users. This content and its use are governed by the Quantstamp       #
# Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.      #
#                                                                                                  #
####################################################################################################

import unittest
import uuid

from stop import Stop
from stop import __handle_sigkill_signal as handle

from unittest.mock import patch


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
        with patch('sys.exit') as exit_mock:
            Stop.sigkill()
        exit_mock.assert_called_once_with(0)

    def test_normal(self):
        with patch('sys.exit') as exit_mock:
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
            Stop.normal()
            exit_mock.assert_called_once_with(0)
            self.assertTrue(stoppables[0].is_stopped)
            self.assertTrue(stoppables[1].is_stopped)
            self.assertTrue(stoppables[2].is_stopped)
            self.assertTrue(stoppables[3].is_stopped)

    def test_set_logger(self):
        orioginal_logger = Stop._Stop__logger
        Stop.set_logger(15)
        self.assertEqual(15, Stop._Stop__logger)
        Stop._Stop__logger = orioginal_logger

    def test_error(self):
        with patch('sys.exit') as exit_mock:
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
            error_code = 17
            Stop.error("Some error", error_code)
            self.assertTrue(stoppables[0].is_stopped)
            self.assertTrue(stoppables[1].is_stopped)
            self.assertTrue(stoppables[2].is_stopped)
            self.assertTrue(stoppables[3].is_stopped)
            exit_mock.assert_called_once_with(error_code)

    def test_handle_sigkill_signal(self):
        with patch('sys.exit') as exit_mock:
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
            handle(15, 0)
            self.assertTrue(handle.stopping)
            exit_mock.assert_called_once_with(0)
            self.assertTrue(stoppables[0].is_stopped)
            self.assertTrue(stoppables[1].is_stopped)
            self.assertTrue(stoppables[2].is_stopped)
            self.assertTrue(stoppables[3].is_stopped)
            # this should just return now
            self.assertIsNone(handle(15, 0))
            exit_mock.assert_called_once_with(0)
            handle.stopping = False

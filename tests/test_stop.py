import unittest
import uuid

from stop import Stop


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

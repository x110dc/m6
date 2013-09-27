import unittest
from datetime import datetime

from configobj import ConfigObj

from subscribers.subscriber import Subscriber
from subscribers.subscriber import dthandler


class TestSubscriber(unittest.TestCase):

    def setUp(self):
        self.config = ConfigObj('test_data/config')['cube']
        self.test_data = {'foo': 'bar', 'baz': 'quux'}

    def test_seen(self):
        # we pass in an empty dict for state
        # this is a shelve normally:
        subscriber = Subscriber(state=dict())
        actual = subscriber.seen(self.test_data)
        # first off it shouldn't be seen:
        self.assertFalse(actual)
        actual = subscriber.seen(self.test_data)
        # but second time it is:
        self.assertTrue(actual)

    def test_dthandler(self):
        self.assertRaises(TypeError, dthandler, dict(foo='bar'))
        expected = '2013-01-01T00:00:00'
        actual = dthandler(datetime(year=2013, month=1, day=1))
        self.assertEqual(expected, actual)

import unittest
import datetime
from datetime import timedelta
import json
from publishers import google_calendar
import pytz


class TestCalendar(unittest.TestCase):

    def setUp(self):
        with open("./test_data/google_calendar.json", 'r') as input_file:
            self.input_json = input_file.read()
        with open("./test_data/calendar_processed.json", 'r') as output:
            self.output_json = json.load(output)
        self.calendar_item = {
            u'status': u'confirmed',
            u'kind': u'calendar#event',
            u'end': {u'dateTime': u'2013-04-26T15:00:00-05:00'},
            u'created': u'2013-03-25T16:52:07.000Z',
            u'iCalUID': u'm9l2lnsc2eb9e2q0tf8an27878@google.com',
            u'id': u'm9l2lnsc2eb9e2q0tf8an27878_20130426T180000Z',
            u'reminders': {u'useDefault': False},
            u'updated': u'2013-04-25T17:50:26.268Z',
            u'summary': u'coding for Fubar',
            u'start': {u'dateTime': u'2013-04-26T13:00:00-05:00'},
            u'creator': {u'self': True,
                         u'displayName': u'First Last',
                         u'email': u'first.last@example.com'},
            u'recurringEventId': u'm9l2lnsc2eb9e2q0tf8an27878',
            u'organizer': {u'self': True,
                           u'displayName': u'First Last',
                           u'email': u'first.last@example.com'},
            u'sequence': 0,
            u'originalStartTime': {u'timeZone': u'America/Chicago',
                                   u'dateTime': u'2013-04-26T13:00:00-05:00'}
        }
        self.input = [
            {'status': u'cancelled',
             'description': None,
             'end_date': '2013-04-26 18:20:00+00:00',
             'title': u'coding for Fubar',
             'calendar_name': 'first.last@example.com',
             'duration': 2.3333333333333335,
             'organizer': {u'self': True,
                           u'displayName': u'First Last',
                           u'email': u'first.last@example.com'},
             'start_date': '2013-04-26 16:00:00+00:00'},
            {'status': u'confirmed',
             'description': None,
             'end_date': '2013-04-28 00:00:00+00:00',
             'title': u'MM anniversary party',
             'calendar_name': 'first.last@example.com',
             'duration': 24.0,
             'organizer': {u'self': True,
                           u'displayName': u'First Last',
                           u'email': u'first.last@example.com'},
             'start_date': '2013-04-27 00:00:00+00:00'}]

    def test_cancelled(self):
        expected = [
            {'status': u'confirmed',
             'description': None,
             'end_date': '2013-04-28 00:00:00+00:00',
             'title': u'MM anniversary party',
             'calendar_name': 'first.last@example.com',
             'duration': 24.0,
             'organizer': {u'self': True,
                           u'displayName': u'First Last',
                           u'email': u'first.last@example.com'},
             'start_date': '2013-04-27 00:00:00+00:00'}]

        out = google_calendar.filter_cancelled_events(self.input)
        self.assertEqual(expected, out)

    def test_no_end_date(self):
        del self.input[0]['end_date']
        expected = [
            {'status': u'confirmed',
             'description': None,
             'end_date': '2013-04-28 00:00:00+00:00',
             'title': u'MM anniversary party',
             'calendar_name': 'first.last@example.com',
             'duration': 24.0,
             'organizer': {u'self': True,
                           u'displayName': u'First Last',
                           u'email': u'first.last@example.com'},
             'start_date': '2013-04-27 00:00:00+00:00'}]

        out = google_calendar.filter_no_end_date(self.input)
        self.assertEqual(expected, out)

    def test_transform(self):
        actual = google_calendar.transform_data(
            [self.calendar_item],
            'first.last@example.com')
        actual = actual[0]
        self.assertEqual('calendar', actual['source'])
        self.assertEqual('first.last@example.com',
                         actual['calendar_name'])
        self.assertEqual('coding for Fubar', actual['title'])
        self.assertEqual('m9l2lnsc2eb9e2q0tf8an27878@google.com',
                         actual['key'])

    def test_transform_comment(self):
        input = json.loads(self.input_json)['items'][13]
        actual = google_calendar.transform_data(
            [input],
            'first.last@example.com')
        self.assertEqual('bar', actual[0]['tag'])

    def test_get_date(self):
        item = {'start': {u'dateTime': u'2013-04-30T13:00:00-05:00'}}
        actual = google_calendar.get_date(item, 'start')
        expected = datetime.datetime(2013, 4, 30, 13, 0,
                                     tzinfo=pytz.timezone('UTC'))

        self.assertEqual(expected, actual)
        item = {'start': {u'date': u'2013-04-30T13:00:00-05:00'}}
        actual = google_calendar.get_date(item, 'start')
        expected = datetime.datetime(2013, 4, 30, 13, 0,
                                     tzinfo=pytz.timezone('UTC'))
        self.assertEqual(expected, actual)

        item = {'start': {u'bogus': u'2013-04-30T13:00:00-05:00'}}
        actual = google_calendar.get_date(item, 'start')
        expected = None
        self.assertEqual(expected, actual)

    @unittest.skip('moving filtering older entries to consumers')
    def test_filter_older_entries(self):
        now = datetime.datetime.now().replace(tzinfo=pytz.timezone('UTC'))
        self.input[0]['end_date'] = now.isoformat()
        actual = google_calendar.filter_older_entries(self.input)
        expected = [self.input[0]]
        # now should always be true:
        self.assertEqual(expected, actual)

        self.input[0]['end_date'] = (now - timedelta(days=5)).isoformat()
        actual = google_calendar.filter_older_entries(self.input)
        self.assertEqual([], actual)
        # but we can also specify the range:
        actual = google_calendar.filter_older_entries(self.input, days_range=6)
        expected = [self.input[0]]
        self.assertEqual(expected, actual)

    @unittest.skip('don\'t want to actually hit API')
    def test_google_api(self):
        result = google_calendar.go('first.last@example.com')
        self.assertIsInstance(result, list)
        # the result should convert to JSON without error:
        self.assertTrue(json.dumps(result))

    def test_exclude_declined(self):
        input = {
            u'status': u'confirmed',
            u'attendeesOmitted': True,
            u'kind': u'calendar#event',
            u'end': {u'dateTime': u'2013-05-11T00:00:00-05:00'},
            u'description': u'Get ready to grab your closest Flak Cannon and',
            u'created': u'2013-04-18T17:06:59.000Z',
            u'iCalUID': u'u8p1i9fmdrt6bmdp281eitc7us@google.com',
            u'locked': True,
            u'htmlLink': u'https://plus.google.com/events/cubmdp281eitc7us',
            u'sequence': 0,
            u'updated': u'2013-05-07T00:35:08.690Z',
            u'visibility': u'private',
            u'summary': u'Unreal Foo Bar',
            u'start': {u'dateTime': u'2013-05-10T17:00:00-05:00'},
            u'etag': u'"vPGZK2Ckfad3ZtNE/Z2NhbDAwMDAxMzY3ODg2OTA4NjkwMDAw"',
            u'location': u'206 E 9th St',
            u'reminders': {u'useDefault': True},
            u'attendees': [{u'organizer': True,
                            u'displayName': u'Foo Bar',
                            u'id': u'100871926551161341163',
                            u'responseStatus': u'accepted'},
                           {u'self': True,
                            u'displayName': u'First Last',
                            u'id': u'113661856195681306883',
                            u'responseStatus': u'declined'}],
            u'organizer': {u'displayName': u'Foo Bar',
                           u'id': u'100871926551161341163'},
            u'creator': {u'displayName': u'Foo Bar',
                         u'id': u'100871926551161341163'},
            u'id': u'u8p1i9fmdrt6bmdp281eitc7us'}
        actual = google_calendar.filter_declined_entries([input])
        self.assertEqual([], actual)

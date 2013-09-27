import datetime
import unittest
from StringIO import StringIO

import pytz
from configobj import ConfigObj
from lxml import etree

from publishers import google_calendar
from subscribers.harvest import Harvest

parser = etree.XMLParser(remove_blank_text=True)


def to_xml_string(data):
    return etree.tostring(etree.parse(StringIO(data), parser))


class TestHarvestCalendar(unittest.TestCase):

    def setUp(self):
        config = ConfigObj('test_data/config')['harvest']
        self.harvester = Harvest(config, dict())
        # defining this should prevent it from hitting the server for it:
        self.harvester.projects = {
            u'Miscellaneous': {'project_id': 535468, 'task_id': 1685399},
            u'PTO, Holidays, etc.': {'project_id': 755756, 'task_id': 601929},
            u'People Operations': {'project_id': 535465, 'task_id': 1685399},
            u'Server Department Work': {
                'project_id': 2825129,
                'task_id': 1685399},
            u'Training': {'project_id': 3181195, 'task_id': 1685399},
            u'Welcome Project': {'project_id': 1059999, 'task_id': 1685399}}

        self.input = [
            {u'status': u'confirmed',
             u'description': None,
             u'end_date': u'2013-05-02 15:00:00+00:00',
             u'title': u'coding for Fubar',
             u'calendar_name': u'first.last@example.com',
             u'source': u'calendar',
             u'key': 'bogus',
             u'seconds':  7200,
             u'duration': 2.0,
             u'organizer': {
                 u'self': True,
                 u'displayName': u'First Last',
                 u'email': u'first.last@example.com'},
             u'start_date': u'2013-05-02 13:00:00+00:00'}]
        self.now = datetime.datetime.now().replace(tzinfo=pytz.timezone('UTC'))
        for x in self.input:
            x['end_date'] = self.now.isoformat()

    def test_parse_calendar_to_harvest(self):

        results = self.harvester.process(self.input)

        expected = """
        <request>
            <notes>coding for Fubar\n</notes>
            <hours>2.0</hours>
            <project_id type="integer">2825129</project_id>
            <task_id type="integer">1685399</task_id>
            <spent_at type="date">{}</spent_at>
        </request>
        """.format(self.now.date())

        expected = to_xml_string(expected)
        actual = to_xml_string(results[0].post_data())
        self.assertEqual(expected, actual)

    @unittest.skip('don\'t want to POST to Harvest every test run')
    def test_harvest_api(self):
        result = google_calendar.go('first.last@example.com')
        now = datetime.datetime.now().replace(tzinfo=pytz.timezone('UTC'))
        now = now.isoformat()
        for x in result:
            x['end_date'] = now
        self.assertIsInstance(result, list)
        results = self.harvester.process(result, {})
        for item in results:
            item.submit()


class TestHarvestOmniFocus(unittest.TestCase):

    def setUp(self):
        config = ConfigObj('test_data/config')['harvest']
        self.harvester = Harvest(config, dict())
        # defining this should prevent it from hitting the server for it:
        self.harvester.projects = {
            u'Miscellaneous': {'project_id': 535468, 'task_id': 1685399},
            u'PTO, Holidays, etc.': {'project_id': 755756, 'task_id': 601929},
            u'People Operations': {'project_id': 535465, 'task_id': 1685399},
            u'Server Department Work': {
                'project_id': 2825129,
                'task_id': 1685399},
            u'Training': {'project_id': 3181195, 'task_id': 1685399},
            u'Welcome Project': {'project_id': 1059999, 'task_id': 1685399}}

        self.input = [
            {"project": ["MM", None, "stuff"],
             "source": "omnifocus",
             "estimatedMinutes": "0",
             "dateCompleted": "2013-05-13T18:25:45.642Z",
             "task": "do something dumb",
             "context": ["MM"],
             "disposition": "completed"}
        ]

    def test_parse_omnifocus_to_harvest(self):

        results = self.harvester.process(self.input)
        actual = to_xml_string(results[0].post_data())
        expected = """
        <request>
            <notes>MM/stuff\n&#8226; do something dumb\n</notes>
            <hours>0.0</hours>
            <project_id type="integer">2825129</project_id>
            <task_id type="integer">1685399</task_id>
            <spent_at type="date">2013-05-13</spent_at>
        </request>
        """
        expected = to_xml_string(expected)
        actual = to_xml_string(results[0].post_data())
        self.assertEqual(expected, actual)

    def test_non_work_project(self):
        self.input[0]['project'] = 'bogus'
        actual = self.harvester.process(self.input)
        expected = []
        self.assertEqual(expected, actual)

    def test_deleted_task(self):
        input = {u'project': [None],
                 u'source': u'omnifocus',
                 u'task': u'yc62CRnLTzreaDW',
                 u'context': [None],
                 u'disposition': u'deleted'}
        actual = self.harvester.process_omnifocus(input)
        self.assertEqual(None, actual)


class TestGit(unittest.TestCase):

    def setUp(self):
        config = ConfigObj('test_data/config')['harvest']
        self.harvester = Harvest(config, dict())
        # defining this should prevent it from hitting the server for it:
        self.harvester.projects = {
            u'Miscellaneous': {'project_id': 535468, 'task_id': 1685399},
            u'PTO, Holidays, etc.': {'project_id': 755756, 'task_id': 601929},
            u'People Operations': {'project_id': 535465, 'task_id': 1685399},
            u'Server Department Work': {
                'project_id': 2825129,
                'task_id': 1685399},
            u'Training': {'project_id': 3181195, 'task_id': 1685399},
            u'Welcome Project': {'project_id': 1059999, 'task_id': 1685399}}

        self.input = [
            {"author": "first.last@3405b383-3743-4ad0-afb9-c69810cec0ab",
             "source": "Git",
             "key": "foo",
             "seconds": 0,
             "branch": "",
             "date": "2013-05-16 15:52:52 +0000",
             "end_date": "2013-05-16 15:52:52 +0000",
             "notes": [
                 "tests for ext info\n\ngit-svn-id: "
                 "https://svn.r.example.com/foo-energy-pp/branches"
                 "/Server/621_%5BServer%5D_Logic_to_determine_if_the_reel"
                 "_is_full_or_cut_@1016 3405b383-3743-4ad0-afb9-c69810cec0ab"
             ],
             "repo_name": "foo"
             }
        ]
        self.now = datetime.datetime.now().replace(tzinfo=pytz.timezone('UTC'))
        for x in self.input:
            x['end_date'] = self.now.isoformat()

    def test_note_formatting(self):
        results = self.harvester.process(self.input)
        actual = results[0]

        self.assertEqual('0.0', actual.hours)
        self.assertEqual(self.now.strftime('%Y-%m-%d'), actual.spent_at)
        self.assertEqual(['foo', 'tests for ext info\n\n'
                          'git-svn-id: https://svn.r.example.com/'
                          'foo-energy-pp/branches/Server/621_%5'
                          'BServer%5D_Logic_to_determine_if_the_reel_is_full'
                          '_or_cut_@1016 3405b383-3743-4ad0-afb9-'
                          'c69810cec0ab'], actual.notes)


class TestGitAggregation(unittest.TestCase):

    def setUp(self):
        config = ConfigObj()
        self.harvester = Harvest(config, dict())

        self.input = [
            {'author': 'first.last@bogus',
             'end_date': '2013-05-16 15:52:52 +0000',
             'source': 'Git',
             'seconds': 500,
             'notes': ['foo'],
             'key': 'bar-foo',
             'repo_name': 'foo'
             },
            {'author': 'first.last@bogus',
             'end_date': '2013-05-17 15:52:52 +0000',
             'source': 'Git',
             'seconds': 5,
             'key': 'bar-foo',
             'notes': ['bar'],
             'repo_name': 'foo'
             },
            {'author': 'first.last@bogus',
             'source': 'Git',
             'seconds': 1000,
             'key': 'bar-foo',
             'end_date': '2013-05-16 15:52:52 +0000',
             'notes': ['baz'],
             'repo_name': 'foo'
             },
            {'author': 'first.last@bogus',
             'source': 'Git',
             'seconds': 2000,
             'key': 'bar-bar',
             'end_date': '2013-05-16 15:52:52 +0000',
             'notes': ['quux'],
             'repo_name': 'foo'
             },
            {'author': 'first.last@bogus',
             'source': 'Git',
             'seconds': 7000,
             'key': 'bar-bar',
             'end_date': '2013-05-16 15:52:52 +0000',
             'notes': ['fizzle'],
             'repo_name': 'foo'
             },
            {'author': 'first.last@bogus',
             'source': 'Git',
             'seconds': 8000,
             'key': 'bar-bar',
             'end_date': '2013-05-16 15:52:52 +0000',
             'notes': ['zazz'],
             'repo_name': 'foo'
             },
            {'author': 'first.last@bogus',
             'source': 'Git',
             'seconds': 15000,
             'key': 'bar-bar',
             'end_date': '2013-05-16 15:52:52 +0000',
             'notes': ['yazoo'],
             'repo_name': 'foo'
             },
        ]

    def test_aggregation(self):
        actual = self.harvester.aggregate([self.input[0], self.input[2],
                                           self.input[3]])
        expected = [{'key': 'bar-bar', 'notes': ['bar-bar',
                                                 'quux'],
                     'end_date': '2013-05-16',
                     'seconds': 2000},
                    {'key': 'bar-foo', 'notes': ['bar-foo',
                                                 'foo', 'baz'],
                     'end_date': '2013-05-16',
                     'seconds': 1500}]
        self.assertEqual(expected, actual)

    def test_with_large_item(self):
        """
        The 'yazoo' item should end up by itself since it's over the time
        limit.  But note that the above list shouldn't happen as-is because
        it mixes entries from two different dates.  They are aggregated here
        but normally they'd be separated prior.
        """
        actual = self.harvester.aggregate(self.input)
        expected = [{'key': 'bar-bar', 'notes': ['bar-bar',
                                                 'quux', 'fizzle'],
                     'end_date': '2013-05-16',
                     'seconds': 9000},
                    {'key': 'bar-bar', 'notes': ['bar-bar',
                                                 'zazz'],
                     'end_date': '2013-05-16',
                     'seconds': 8000},
                    {'key': 'bar-bar', 'notes': ['bar-bar',
                                                 'yazoo'],
                     'end_date': '2013-05-16',
                     'seconds': 15000},
                    {'key': 'bar-foo', 'notes': ['bar-foo',
                                                 'foo', 'bar', 'baz'],
                     'end_date': '2013-05-16',
                     'seconds': 1505}]
        self.assertEqual(expected, actual)

    def test_single_item(self):
        actual = self.harvester.aggregate([self.input[0]])
        expected = [{'seconds': 500, 'notes': ['bar-foo',
                                               'foo'], 'key':
                     'bar-foo', 'end_date': '2013-05-16', }]
        self.assertEqual(expected, actual)

    def test_aggregation_2(self):
        del self.input[1]
        del self.input[5]
        actual = self.harvester.aggregate(self.input)
        expected = [{'key': 'bar-bar', 'notes': ['bar-bar',
                                                 'quux', 'fizzle'],
                     'end_date': '2013-05-16',
                     'seconds': 9000},
                    {'key': 'bar-bar', 'notes': ['bar-bar',
                                                 'zazz'],
                     'end_date': '2013-05-16',
                     'seconds': 8000},
                    {'key': 'bar-foo', 'notes': ['bar-foo',
                                                 'foo', 'baz'],
                     'end_date': '2013-05-16',
                     'seconds': 1500}]
        self.assertEqual(expected, actual)

    def test_aggregation_by_day(self):
        """should return a dict with two keys, one for each day,
        each key should have a list as a value
        """
        results = self.harvester.group_by_day(self.input)
        self.assertEqual(2, len(results))
        self.assertEqual(['2013-05-16', '2013-05-17'], results.keys())
        self.assertEqual(6, len(results['2013-05-16']))
        self.assertEqual(1, len(results['2013-05-17']))


class TestAggregateOmniFocus(unittest.TestCase):

    def setUp(self):
        self.input = [
            {'project': ['A', None, 'B'],
             'key': 'A/B',
             'source': 'omnifocus',
             u'end_date': u'2013-05-02 15:00:00+00:00',
             'notes': ['foo'],
             'estimatedMinutes': '0',
             'seconds': 100,
             'task': 'foo',
             'context': ['MM'],
             'disposition': 'completed'},
            {'project': ['A', None, 'C'],
             'key': 'A/C',
             'source': 'omnifocus',
             u'end_date': u'2013-05-02 15:00:00+00:00',
             'estimatedMinutes': '0',
             'seconds': 100,
             'notes': ['bar'],
             'task': 'bar',
             'context': ['MM'],
             'disposition': 'completed'},
            {'project': ['A', None, 'B'],
             'key': 'A/C',
             'source': 'omnifocus',
             'estimatedMinutes': '0',
             'notes': ['baz'],
             'seconds': 100,
             u'end_date': u'2013-05-02 15:00:00+00:00',
             'task': 'baz',
             'context': ['MM'],
             'disposition': 'completed'},
        ]

    def test_omnifocus_aggregation(self):

        config = ConfigObj()
        self.harvester = Harvest(config, dict())
        actual = self.harvester.aggregate(self.input)
        expected = [{'end_date': '2013-05-02',
                     'key': 'A/C',
                     'notes': ['A/C', 'bar', 'baz'],
                     'seconds': 200},
                    {'end_date': '2013-05-02', 'key': 'A/B',
                     'notes': ['A/B', 'foo'], 'seconds': 100}]

        self.assertEqual(expected, actual)


class TestJira(unittest.TestCase):

    def setUp(self):
        self.input = [
            {
                "comment": "foo!",
                "issue_description": "http://replay.r.example.com/"
                "Timeline/Index/a07b0ce2-73a2-4951-956d-46689aa2255e",
                "created": "2013-05-14T14:47:29.941-0500",
                "issue_key": "MMSANDBOX-2803",
                "source": "JIRA",
                "timeSpentSeconds": 600
            },
            {
                "comment": "bazbazz!",
                "issue_description": "http://replay.r.example.com/"
                "Timeline/Index/a07b0ce2-73a2-4951-956d-46689aa2255e",
                "created": "2013-05-14T14:49:58.625-0500",
                "issue_key": "MMSANDBOX-2803",
                "source": "JIRA",
                "timeSpentSeconds": 900
            }
        ]


class TestNoEndDate(unittest.TestCase):

    def setUp(self):

        config = ConfigObj('test_data/config')['harvest']
        self.harvester = Harvest(config, dict())
        # defining this should prevent it from hitting the server for it:
        self.harvester.projects = {
            u'Miscellaneous': {'project_id': 535468, 'task_id': 1685399},
            u'PTO, Holidays, etc.': {'project_id': 755756, 'task_id': 601929},
            u'People Operations': {'project_id': 535465, 'task_id': 1685399},
            u'Server Department Work': {
                'project_id': 2825129,
                'task_id': 1685399},
            u'Training': {'project_id': 3181195, 'task_id': 1685399},
            u'Welcome Project': {'project_id': 1059999, 'task_id': 1685399}}

        self.input = [
            {"project": ["Health", None, "MM"],
             "source": "omnifocus",
             "estimatedMinutes": "0",
             "task": "do something dumb",
             "context": ["MM"],
             "disposition": "completed"}
        ]
        now = datetime.datetime.now().replace(tzinfo=pytz.timezone('UTC'))
        self.now = now.strftime('%Y-%m-%d')

    def test_entry_no_end_date(self):

        results = self.harvester.process(self.input)
        actual = to_xml_string(results[0].post_data())
        expected = """
        <request>
            <notes>Health/MM\n&#8226; do something dumb\n</notes>
            <hours>0.0</hours>
            <project_id type="integer">2825129</project_id>
            <task_id type="integer">1685399</task_id>
            <spent_at type="date">{}</spent_at>
        </request>
        """.format(self.now)
        expected = to_xml_string(expected)
        actual = to_xml_string(results[0].post_data())
        self.assertEqual(expected, actual)

import unittest
from publishers.jira_pub import parse_html
from publishers.jira_pub import get_worklogs
from publishers.jira_pub import get_logged_issues
from publishers.jira_pub import get_activity_stream
import feedparser


class TestParseActivityStream(unittest.TestCase):

    def setUp(self):
        self.html = ('<a class="activity-item-user activity-item-author"'
                     'href="https://jira.r.example.com/secure/'
                     'ViewProfile.jspa?name=daniel.last">Daniel '
                     'Last</a> logged \'0.25h\' on       <a href="'
                     'https://jira.r.example.com/browse/MMSANDBOX'
                     '-2803">MMSANDBOX-2803 - test testpad #2</a>')
        self.atom_xml = open('test_data/atom.xml', 'r').read()
        self.issues = ['MMSANDBOX-2803']

    def test_parse_html(self):
        actual = parse_html(self.html)
        expected = ['Daniel Last', "logged '0.25h' on",
                    'MMSANDBOX-2803 - test testpad #2']
        self.assertEqual(expected, actual)

    def test_get_logged_issues(self):
        actual = get_logged_issues(self.atom_xml)
        expected = ['FOOBAR-882', 'MMSANDBOX-2803']
        self.assertEqual(expected, actual)

    def test_get_activity_stream(self):
        # make sure the activity stream parses
        xml = get_activity_stream()
        actual = feedparser.parse(xml)
        self.assertTrue(isinstance(actual, dict))

    @unittest.skip('talks to JIRA directly')
    def test_get_worklogs(self):
        actual = get_worklogs(self.issues)
        expected = [{'comment': u'quux!',
                     'created': u'2013-05-14T14:09:26.566-0500',
                     'issue_description': u'http://replay.r.example.com'
                     '/Timeline/Index/a07b0ce2-73a2-4951-956d-46689aa2255e',
                     'issue_key': 'MMSANDBOX-2803',
                     'source': 'JIRA',
                     'timeSpentSeconds': 10800},
                    {'comment': u'foo!',
                     'created': u'2013-05-14T14:47:29.941-0500',
                     'issue_description': u'http://replay.r.example.com'
                     '/Timeline/Index/a07b0ce2-73a2-4951-956d-46689aa2255e',
                     'source': 'JIRA',
                     'issue_key': 'MMSANDBOX-2803',
                     'timeSpentSeconds': 600},
                    {'comment': u'bazbazz!',
                     'created': u'2013-05-14T14:49:58.625-0500',
                     'issue_description': u'http://replay.r.example.com'
                     '/Timeline/Index/a07b0ce2-73a2-4951-956d-46689aa2255e',
                     'source': 'JIRA',
                     'issue_key': 'MMSANDBOX-2803',
                     'timeSpentSeconds': 900}]
        self.assertEqual(expected, actual)

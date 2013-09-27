# TODO: write test for one without a context
from lxml import etree
#import shelve
import unittest
import StringIO
from configobj import ConfigObj

#import sys
#sys.path.insert(0, '/Users/danielc/Git/M6')

from publishers.omnifocus import OmniFocus
from publishers.omnifocus import get_project
from publishers.omnifocus import get_context
#from publishers.omnifocus import follow_idref
from publishers.omnifocus import ns

#xml = open("./test_data/nested-contexts.xml", 'r').read()
#root = etree.fromstring(xml)
#node = root.xpath(
#        '//of:task/of:name[normalize-space(text())="bogus1234"]',
#    namespaces=ns)[0]
##print "/".join(get_context(node))
#assert ['bogus3', 'Daily', 'Personal']==get_context(node)
#
#xml = open("./test_data/out-of-order.xml", 'r').read()
#root = etree.fromstring(xml)
#node = root.xpath(
#        '//of:task/of:name[normalize-space(text())="H202"]',
#    namespaces=ns)[0]
#assert ['Shopping', 'CVS']==get_context(node)
#
#
#
#xml = open("./test_data/deleted-example.xml", 'r').read()
#root = etree.fromstring(xml)
#node = root.xpath(
#        '//of:task[@id="jC6tYVQXXGk"]',
#    namespaces=ns)[0]
#from ipdb import set_trace; set_trace()
#project = get_project(node)
#context = get_context(node)
#store = shelve.open("./shelve", flag='r')
#identity = node.get('id')
#name = get_name(identity, store)
#assert 'bogus3'==name


class TestOmniFocus(unittest.TestCase):

    def setUp(self):
        config = ConfigObj('test_data/config')['omnifocus']
        self.of = OmniFocus(config, dict())
        self.xml_file = open("./test_data/nested-contexts.xml", 'r')
        self.xml = self.xml_file.read()
        self.root = etree.fromstring(self.xml)
        self.node = self.root.xpath(
            '//of:task/of:name[normalize-space(text())="bogus1234"]',
            namespaces=ns)[0]
        self.xml_file.close()

    def test_get_context(self):
        expected = ['bogus3', 'Daily', 'Personal']
        actual = get_context(self.node)
        self.assertEqual(expected, actual)

    def test_no_context_or_project(self):
        xml_file = open(
            "./test_data/completion-without-context-or-project.xml", 'r')
        xml = xml_file.read()
        root = etree.fromstring(xml)
        node = root.xpath(
            '//of:task/of:name[normalize-space(text())="bogus"]',
            namespaces=ns)[0]
        xml_file.close()
        self.assertIsInstance(get_context(node), list)
        self.assertEqual([None], get_context(node))

    def test_estimated_minutes(self):
        xml_file = open(
            "./test_data/completion-without-context-or-project.xml", 'r')
        xml = xml_file.read()
        root = etree.fromstring(xml)
        node = root.xpath(
            '//of:task/of:name[normalize-space(text())="bogus"]',
            namespaces=ns)[0]
        xml_file.close()
        actual = self.of.get_estimated_minutes(node)
        expected = '55'
        self.assertIsInstance(get_context(node), list)
        self.assertEqual(expected, actual)

#    def test_too_old(self):
#        expected = False
#        actual = too_old(datetime.datetime.now().isoformat())
#        self.assertEqual(expected, actual)
#        expected = True
#        actual = too_old('2013-01-13T17:35:03.124Z')
#        self.assertEqual(expected, actual)


class TestProcessTask(unittest.TestCase):
    def setUp(self):

        config = ConfigObj('test_data/config')['omnifocus']
        self.of = OmniFocus(config, dict())
        self.xml_file = open("./test_data/contents-test.xml", 'r')
        self.xml = self.xml_file.read()
        self.xml_file.close()
        self.context = etree.iterparse(
            StringIO.StringIO(self.xml),
            tag="{http://www.omnigroup.com/namespace/OmniFocus/v1}task")

#    def test_process_task(self):
#
#        for action, element in self.context:
#            operation = element.get('op')
#            identity = element.get('id')
#            if not identity or not operation:
#                continue
#            for child in element.iterchildren():
#                if child.tag.endswith('completed'):
#                    actual = self.of.process_task(element, identity)
#
#            expected = {'project': ['Bogus', None, 'bogus2'],
#                        'source': 'omnifocus',
#                        'estimatedMinutes': '10',
#                        'dateCompleted': '2013-05-13T18:25:45.642Z',
#                        'end_date': '2013-05-13T18:25:45.642Z',
#                        'task': 'do something dumb',
#                        'context': ['MM'],
#                        'disposition': 'completed'}
#        from ipdb import set_trace; set_trace()
#        self.assertEqual(expected, actual)


class TestProcessNonUpdateTask(unittest.TestCase):
    def setUp(self):

        config = ConfigObj('test_data/config')['omnifocus']
        self.of = OmniFocus(config, dict())
        self.xml_file = open("./test_data/contents-non-update.xml", 'r')
        self.xml = self.xml_file.read()
        self.xml_file.close()
        self.context = etree.iterparse(
            StringIO.StringIO(self.xml),
            tag="{http://www.omnigroup.com/namespace/OmniFocus/v1}task")
        self.expected = [{'context': ['Internet', 'Research'],
                         'dateCompleted': '2013-06-12T18:37:03.517Z',
                         'disposition': 'completed',
                         'end_date': '2013-06-12T18:37:03.517Z',
                         'estimatedMinutes': '10',
                         'project': ['IT', 'Backup gmail'],
                         'source': 'omnifocus',
                         'task': 'research how to back up Gmail'}]

    def test_process_non_update_task(self):
        for action, element in self.context:
            identity = element.get('id')
            for child in element.iterchildren():
                if child.tag.endswith('completed'):
                    actual = self.of.process_task(element, identity)
        self.assertEqual(self.expected, [actual])

    def test_process_xml(self):
        actual = self.of.process_xml(self.xml)
        self.assertEqual(self.expected, actual)


class TestProcessXml(unittest.TestCase):

    def setUp(self):
        self.xml_file = open("./test_data/contents-test.xml", 'r')
        self.xml = self.xml_file.read()
        self.xml_file.close()
        config = ConfigObj('test_data/config')['omnifocus']
        self.of = OmniFocus(config, dict())

    def test_process_xml(self):
        actual = self.of.process_xml(self.xml)

        expected = [{'context': ['MM'],
                     'dateCompleted': '2013-05-13T18:25:45.642Z',
                     'disposition': 'completed',
                     'end_date': '2013-05-13T18:25:45.642Z',
                     'estimatedMinutes': '10',
                     'project': ['Bogus', 'bogus2'],
                     'source': 'omnifocus',
                     'task': 'do something dumb'},
                    {'context': ['MM'],
                     'dateCompleted': '2013-05-13T18:25:45.642Z',
                     'disposition': 'completed',
                     'end_date': '2013-05-13T18:25:45.642Z',
                     'estimatedMinutes': '10',
                     'project': ['Bogus', 'bogus2'],
                     'source': 'omnifocus',
                     'task': 'do something else'}]

        self.assertEqual(expected, actual)


class TestGetProject(unittest.TestCase):

    def setUp(self):
        self.xml_file = open("./test_data/nested-projects.xml", 'r')
        self.xml = self.xml_file.read()
        self.root = etree.fromstring(self.xml)
        self.node = self.root.xpath(
            '//of:task/of:name[normalize-space(text())="bogus5678"]',
            namespaces=ns)[0]
        self.xml_file.close()
        config = ConfigObj('test_data/config')['omnifocus']
        self.of = OmniFocus(config, dict())

    def test_get_project(self):
        expected = ['MM', 'MM-Foobar', None, 'GA']
        actual = get_project(self.node)
        self.assertEqual(expected, actual)

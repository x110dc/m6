#!/usr/bin/env python

import itertools
import json
import logging
import logging.handlers
import os
import re
import shelve
import zipfile
from datetime import datetime, timedelta
from os.path import expanduser
from StringIO import StringIO

import pytz
from configobj import ConfigObj
from dateutil import parser
from lxml import etree

utc = pytz.timezone('UTC')
days_ago = timedelta(days=10)
ns = {'of': 'http://www.omnigroup.com/namespace/OmniFocus/v1'}

xpath_find = etree.XPath("//*[@id = $name]", namespaces=ns)

ids = dict()

config = ConfigObj(expanduser('~/.m6rc'))
log_file = '{}/m6.log'.format(expanduser(config['main']['log_dir']))
logger = logging.getLogger('m6')
logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=500000,
                                               backupCount=5)
logger.addHandler(handler)


def follow_idref(element):
    '''
    Given an element with an 'idref' attribute, return the
    element it references
    '''
    if 'idref' in element.keys():
        idref = element.get('idref')
        # cache results because xpath is slow:
        if idref in ids:
            return ids[idref]

        #xpath = '//*[@id="{}"]'.format(element.get('idref'))
        #node = xpath_evaluator('//*[@id="{}"]'.format(
        # element.get('idref')))[0]
        node = xpath_find(element, name=element.get('idref'))[0]
        #node = element.xpath(xpath, namespaces=ns)[0]
        ids[idref] = node
        return node
    return element


def get_context(element):
    '''
    Given an element traverse the tree recursively to find
    its context if there is one
    '''
    if not element.tag.endswith('context'):
        context = element.xpath('../of:context', namespaces=ns)
        if not context:
            return [None]
        element = context[0]
    element = follow_idref(element)
    child = element.xpath('of:context', namespaces=ns)
    name = element.xpath('of:name', namespaces=ns)
    if name:
        name = name[0].text.strip()
    else:
        name = None

    # if it doesn't have a child context, return:
    if not child:
        return [name]
    # if it does, recurse:
    return get_context(child[0]) + [name]


def get_project(element):

    if not element.tag.endswith(('task', 'project', 'folder')):
        task = element.xpath(
            '../of:task|../of:project|../of:folder', namespaces=ns)
        if not task:
            return [None]
        element = task[0]
    element = follow_idref(element)
    child = element.xpath('of:project|of:task|of:folder', namespaces=ns)
    name = element.xpath('of:name', namespaces=ns)
    if name:
        name = name[0].text.strip()
    else:
        name = None

    # if it doesn't have a child project, return:
    if not child:
        return [name]
    # if it does, recurse:
    return get_project(child[0]) + [name]


def mk_dict(**kwargs):
    my_dict = kwargs
    if 'dateCompleted' in my_dict:
        my_dict['end_date'] = my_dict['dateCompleted']
    my_dict['source'] = 'omnifocus'
    return my_dict


class OmniFocus (object):

    def __init__(self, config=None, id_map=None):
        self.config = config
        self.id_map = id_map

    def get_estimated_minutes(self, element):
        foo = element.xpath(
            'following-sibling::of:estimated-minutes',
            namespaces=ns)
        if foo:
            return foo[0].text.strip()
        return self.config['default_duration']

    def process_task(self, element, identity):
        out = None
        for child in element.iterchildren():
#            if re.match('.*project$', child.tag):
#                return
            if re.match('.*name$', child.tag):
                name = child.text.strip()
                context = [x for x in get_context(child) if x]
                project = [x for x in get_project(child) if x]
                self.id_map[identity] = (name, context, project)
            elif re.match('.*completed$', child.tag):
                completed = child.text.strip()
                context = get_context(child)
                estimated_minutes = self.get_estimated_minutes(child).strip()
                out = mk_dict(
                    project=project, context=context, task=name,
                    dateCompleted=completed,
                    estimatedMinutes=estimated_minutes,
                    disposition="completed")
                logger.info(
                    "{} completed on {} in {} as part of project {}".format(
                        name.encode('utf-8'), completed, context, project))
            elif re.match('.*estimated-minutes$', child.tag):
                completed = child.text
        return out

    def get_saved_of_ids(self, identity):
        if identity in self.id_map:
            return self.id_map[identity]
        return [None, None, None]

    def process_xml(self, xml):

        results = list()
#        context = etree.iterparse(
#            StringIO(xml), # tag='{{{}}}task'.format(ns['of']),
#        )
        tree = etree.parse(StringIO(xml))
        root = tree.getroot()
        global xpath_evaluator
        xpath_evaluator = etree.XPathEvaluator(root)

        for element in root.findall('.//of:completed', namespaces=ns):
            delta = datetime.now().replace(tzinfo=utc) - parser.parse(
                element.text)
            if delta > timedelta(days=int(self.config['days_ago'])):
                continue
            element = element.getparent()
            operation = element.get('op')
            identity = element.get('id')
            if operation == 'delete':
                name, context, project = self.get_saved_of_ids(identity)
                if not name:
                    continue
                output = mk_dict(project=project, context=context, task=name,
                                 disposition="deleted")
                results.append(output)
            else:
                output = self.process_task(element, identity)
                if output:
                    results.append(output)
        return results

    def process_xml_file(self, zip_file, file):
        data = zip_file.read(file)
        out = self.process_xml(data)
        return out

    def go(self, directory):

        results = list()

        for file in os.listdir(directory):
#            if re.match('^0000', file):
#               continue
            logger.debug('processing file {}'.format(file))
            zip_file = zipfile.ZipFile(directory + "/" + file, 'r')
            for name in zip_file.namelist():
                logger.debug('processing XML file {}'.format(name))
                out = self.process_xml_file(zip_file, name)
                results.append(out)
        # flatten list:
        return list(itertools.chain.from_iterable(results))


if __name__ == '__main__':

    config = config['omnifocus']
    directory = os.path.expanduser(config['zip_dir'])
    filename = '{}/omnifocus-ids.shelve'.format(expanduser(config['app_dir']))
    saved_of_ids = shelve.open(filename, flag='c', writeback=True)
    omnifocuser = OmniFocus(config, saved_of_ids)

    result = [x for x in omnifocuser.go(directory) if x]
    saved_of_ids.close()

    print json.dumps(result, indent=2)

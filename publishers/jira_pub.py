#!/usr/bin/env python

import feedparser
from StringIO import StringIO
from lxml import etree
import requests
import json
import re
import urlparse
from os.path import expanduser
from configobj import ConfigObj
from jira.client import JIRA

config = ConfigObj(expanduser('~/.m6rc'))
config = config['jira']

JIRA_HOST = config['server']
USER = config['username']
PASS = config['password']
NUM_ITEMS = config['num_items']


def get_recent_issues():
    jira_options = {'server': 'https://{}'.format(JIRA_HOST)}
    jira_server = JIRA(jira_options, basic_auth=(USER, PASS))
    issues = jira_server.search_issues(
        'updated >= -7d AND participants in (currentUser())')
    return issues


def parse_html(entry):
    """
    Parse the html (within the atom feed) and return a list
    of the text nodes.
    """
    parser = etree.HTMLParser()
    tree = etree.parse(StringIO(entry), parser)
    parsed = [x for x in tree.iter()]
    body = parsed[0]
    # get all the text nodes of the document:
    text = [x.strip() for x in body.itertext()]
    return text


def get_logged_issues(atom_xml):
    """
    Return a list of issue keys that have time logged against them.
    """
    # parse the atom feed
    parsed = feedparser.parse(atom_xml)
    # find the 'title' entries in there that have 'logged' in the
    # text

    entries = [x['title'] for
               x in parsed['entries'] if 'logged' in x['title']]

    issue_keys = list()
    for entry in entries:
        text = parse_html(entry)
        issue_key = re.search(r'^(\S+)', text[2]).group(1)
        issue_keys.append(issue_key)
    return list(set(issue_keys))


def get_activity_stream():
    """
    Get the user's Atlassian Activity Stream.
    """

    url = urlparse.urlunparse(
        ('https', '{}'.format(JIRA_HOST), '/activity', '',
         'maxResults={}&streams=user+IS+{}&os_authType=basic'
         '&title=Activity'.format(NUM_ITEMS, USER),
         ''))
    response = requests.get(url, auth=(USER, PASS))
    return response.content


def get_worklogs(issues):
    """
    Get JIRA worklog entries for a list of issues.
    """

    jira_options = {'server': 'https://{}'.format(JIRA_HOST)}
    jira_server = JIRA(jira_options, basic_auth=(USER, PASS))

    entries = list()

    for issue_key in issues:
        description = jira_server.issue(issue_key).fields.description
        worklogs = jira_server.worklogs(issue=issue_key)
        for worklog in worklogs:
            entry = dict()
            entry['issue_key'] = issue_key
            entry['issue_description'] = description
            entry['timeSpentSeconds'] = worklog.timeSpentSeconds
            entry['created'] = worklog.created
            entry['comment'] = worklog.comment
            entries.append(entry)
            entry['source'] = 'JIRA'
    return entries


if __name__ == '__main__':
    xml_data = get_activity_stream()
    issues = get_logged_issues(xml_data)
    entries = get_worklogs(issues)
    print json.dumps(entries, indent=2)

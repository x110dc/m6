#!/usr/bin/env python

import json
import argparse
from datetime import datetime
from os.path import expanduser
import sys
import hashlib
import shelve
import logging
from datetime import timedelta

from lxml import etree
from configobj import ConfigObj
import requests
import pytz
import dateutil.parser

utc = pytz.timezone('UTC')


class HarvestEntry(object):

    def __init__(self, hours='1', notes=None, project=None, task=None,
                 spent_at=str(datetime.now()), config=None):

        self.notes = notes or list()
        self.config = config
        self.hours = hours
        self.project = project
        self.task = task
        self.spent_at = spent_at
        self.headers = {'Content-Type': 'application/xml',
                        'Accept': 'application/xml'}
        self.url = '{}/{}'.format(config['server'], 'daily/add')

    def append(self, text):
        self.notes.append(text)

    def __str__(self):
        return '{}/{}/{}/{} on {}'.format(self.notes, self.hours,
                                          self.project,
                                          self.task, self.spent_at)

    def post_data(self):

        request = etree.Element('request')
        notes = etree.SubElement(request, 'notes')
#        notes.text = '\n'.join(self.notes) + '\n'
        notes.text = u'\n\u2022 '.join(self.notes) + '\n'

        hours = etree.SubElement(request, 'hours')
        hours.text = self.hours

        project = etree.SubElement(request, 'project_id')
        project.text = self.project
        project.set('type', 'integer')

        task = etree.SubElement(request, 'task_id')
        task.text = self.task
        task.set('type', 'integer')

        spent_at = etree.SubElement(request, 'spent_at')
        spent_at.text = self.spent_at
        spent_at.set('type', 'date')

        return etree.tostring(request, encoding='utf8')

        #<request>
        #  <notes>Test api support</notes>
        #  <hours>3</hours>
        #  <project_id type='integer'>3</project_id>
        #  <task_id type='integer'>14</task_id>
        #  <spent_at type='date'>Tue, 17 Oct 2006</spent_at>
        #</request>

    def submit(self):
        response = requests.post(self.url, auth=(config['username'],
                                                 config['password']),
                                 headers=self.headers, data=self.post_data())

        if response.status_code != 201:
            #logging.debug(response)
            #logging.debug(response.content)
            raise Exception(
                'expected status code 201, received {}'.format(
                    response.status_code))


class Harvest (object):

    def __init__(self, config=None, state=None):
        self.config = config
        self.state = state
        self.count_seen = 0
        self.count_older = 0

    def filter_older_entries(self, entries, days_range=4):

        new_list = list()

        for entry in entries:
            now = datetime.now().replace(tzinfo=utc)
            ago = now - dateutil.parser.parse(entry['end_date'])
            ago = abs(ago)

            if ago <= timedelta(days=days_range):
                new_list.append(entry)
            else:
                self.count_older += 1
                logging.debug("entry is too old to be queued")

        return new_list

    def get_projects(self):

        # make this call once for the life of the program:
        if getattr(self, 'projects', None):
            return self.projects

        self.headers = {'Accept': 'application/json'}
        self.url = '{}/{}'.format(self.config['server'], 'daily')
        response = requests.get(self.url, auth=(self.config['username'],
                                                self.config['password']),
                                headers=self.headers)
        y = json.loads(response.content)['projects']
        # this makes a pretty bold assumption: that the first task_id in the
        # list for a project is the one we want ('Work').  Might want to fix
        # this at some point.
        self.projects = {x['name']: {
            'project_id': x['id'],
            'task_id': x['tasks'][0]['id']} for x in y}
        return self.projects

    def process_jira(self, request):

        request['seconds'] = request['timeSpentSeconds']
        request['notes'] = [request['comment']]

        return request

    def process_git(self, request):

        # default of 10 minutes
        request['hours'] = 10 / 60.0

        return request

    def process_calendar(self, request):

        if request['calendar_name'] != self.config['username']:
            return

        request['notes'] = [request['title']]

        return request

    def process_omnifocus(self, request):

        if request.get('disposition') == 'deleted':
            return

        # exclude anything that's not work:
        if 'MM' not in request['project']:
            return

        # exclude dumb stuff like this:
        if 'maintain work space' in request['project']:
            return

        request['key'] = "/".join(filter(None, request['project']))
        request['notes'] = [request['task']]

        try:
            end_date = dateutil.parser.parse(request['dateCompleted'])
        except KeyError:
            end_date = datetime.now()
        request['end_date'] = str(end_date.date())

        request['seconds'] = int(request['estimatedMinutes']) * 60.0

        return request

    def seen(self, item):
        # this is an effort to make sure that a dictionary with the
        # same key/value pairs always produces the same string representation
        # (by its elements by key):
        string_rep = '{}'.format(sorted(item.items()))
        m = hashlib.md5()
        m.update(string_rep)
        hash = m.hexdigest()

        if hash in self.state:
            self.count_seen += 1
            return True
        self.state[hash] = item
        return False

    def transform_data(self, entries):

        new_list = list()

        for entry in entries:

            new_list.append(entry)
            # if there's no end date use now:
            if 'end_date' not in entry:
                entry['end_date'] = str(datetime.utcnow().replace(
                    tzinfo=utc).isoformat())

        return new_list

    def convert_to_harvest(self, request):

        hours = request['seconds'] / 60.0 / 60
        spent_at = request['end_date']
        notes = request['notes']

        projects = self.get_projects()

        # if the entry has a project defined, use it
        if 'harvest_project' in request:
            project_id = projects[request['harvest_project']]['project_id']
            task_id = projects[request['harvest_project']]['task_id']
        # else use the defined default
        elif self.config['default_project'] in projects:
            project_id = projects[self.config['default_project']]['project_id']
            task_id = projects[self.config['default_project']]['task_id']
        # otherwise use the first one (this could change randomly)
        else:
            project_id = projects[projects.keys()[0]]['project_id']
            task_id = projects[projects.keys()[0]]['task_id']

        entry = HarvestEntry(hours=str(hours), notes=notes,
                             spent_at=spent_at, task=str(task_id),
                             project=str(project_id), config=self.config)

        return entry

    def group_by_day(self, entries):
        days = dict()
        for entry in entries:
            day = dateutil.parser.parse(entry['end_date']).date()
            days.setdefault(str(day), list()).append(entry)
        return days

# TODO: what if there's no 'key'?
# only aggregate Git and OF?  (not calendar or Jira?)

    def standard_dict(self, day=None, group=None):
        x = dict()
        x['end_date'] = day
        x['key'] = group
        x['notes'] = [group] if group else []
        x['seconds'] = 0
        return x

    def aggregate(self, entries):
        new_entries = list()
        groups = dict()

        # group entries by key:
        for entry in entries:
            groups.setdefault(entry['key'], list()).append(entry)

        # all entries in this group should be on the same date
        # TODO: produce warning/exception if not?

        day = str(dateutil.parser.parse(entry['end_date']).date())
        # aggregate them by time spent:
        for group in groups:
            if entry['source'] == 'calendar':
                new_entry = self.standard_dict(day=day)
            else:
                new_entry = self.standard_dict(day=day, group=group)

            for entry in groups[group]:
                #TODO: don't hardcode this 4-hour boundary (config file
                # instead)
                if new_entry['seconds'] + entry['seconds'] > 14400:
                    new_entries.append(new_entry)
                    new_entry = self.standard_dict(day=day, group=group)
                new_entry['notes'].extend(entry['notes'])
                new_entry['seconds'] += entry['seconds']
            new_entries.append(new_entry)

        return new_entries

    def process(self, data):

        entries = list()

        data = self.transform_data(data)
        data = self.filter_older_entries(data)

        # remove entries we've already seen:
        data = [x for x in data if not self.seen(x)]

        # do processing specific to the source of the entry:
        # TODO: catch AttributeError if no such function and skip step?
        for item in data:
            func = getattr(self, 'process_{}'.format(item['source'].lower()))
            entries.append(func(item))

        # remove 'None' items:
        entries = [x for x in entries if x]

        # group entries by day:
        days = self.group_by_day(entries)

        items = list()
        for day in days:
            items.extend(self.aggregate(days[day]))

        entries = [self.convert_to_harvest(x) for x in items]

        return entries


if __name__ == '__main__':

    input = sys.stdin.read()
    config = ConfigObj(expanduser('~/.m6rc'))
    config = config['harvest']
    filename = '{}/harvest-seen.shelve'.format(expanduser(config['app_dir']))
    state = shelve.open(filename, flag='c', writeback=True)
    harvester = Harvest(config, state)
    out = harvester.process(json.loads(input))
    state.close()
    arger = argparse.ArgumentParser()
    arger.add_argument('--dont-submit', action='store_true')
    opts = arger.parse_args()
    for item in out:
        if not opts.dont_submit:
            item.submit()
        else:
            print item
            print item.post_data()
    print '{} items were recorded'.format(len(out))
    print '{} items were excluded because they had already been seen'.format(
        harvester.count_seen)
    print '{} items were excluded because they were too old'.format(
        harvester.count_older)

#!/usr/bin/env python

import argparse
from os.path import expanduser
import httplib2
import json
from datetime import datetime
from datetime import timedelta
import pytz
import dateutil.parser
import re

from configobj import ConfigObj
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run

# TODO: get this from config?
start_query = datetime.now() - timedelta(days=6)
end_query = datetime.now() + timedelta(days=1)

start_query = start_query.strftime('%Y-%m-%dT%H:%M:%SZ')
end_query = end_query.strftime('%Y-%m-%dT%H:%M:%SZ')

utc = pytz.timezone('UTC')


def do_google_oauth_stuff():

# Set up a Flow object to be used if we need to authenticate. This
# sample uses OAuth 2.0, and we set up the OAuth2WebServerFlow with
# the information it needs to authenticate. Note that it is called
# the Web Server Flow, but it can also handle the flow for native
# applications
# The client_id and client_secret are copied from the API Access tab on
# the Google APIs Console

    FLOW = OAuth2WebServerFlow(
        client_id='75216501644.apps.googleusercontent.com',
        client_secret='iYheserUzVsCmqTQ5nRoH-Z1',
        scope='https://www.googleapis.com/auth/calendar',
        user_agent='fetch-cal/0.0.1')

# To disable the local server feature, uncomment the following line:
# FLAGS.auth_local_webserver = False

# If the Credentials don't exist or are invalid, run through the native client
# flow. The Storage object will ensure that if successful the good
# Credentials will get written back to a file.
    #TODO: store this in app dir?
    storage = Storage('calendar.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid is True:
        credentials = run(FLOW, storage)

# Create an httplib2.Http object to handle our HTTP requests and authorize it
# with our good Credentials.
    http = httplib2.Http()
    http = credentials.authorize(http)

# Build a service object for interacting with the API. Visit
# the Google APIs Console
# to get a developerKey for your own application.
    #service = build(serviceName='calendar', version='v3', http=http,
    #                developerKey='AIzaSyCAKtdiJRZkwYjhlfC1m5uqV90_8grRtmw')

    return http


def get_date(entry, item):
    if item in entry:
        if 'dateTime' in entry[item]:
            return dateutil.parser.parse(entry[item]['dateTime']).replace(
                tzinfo=utc)
        elif 'date' in entry[item]:
            return dateutil.parser.parse(entry[item]['date']).replace(
                tzinfo=utc)
        return None


def filter_private_entries(entries):

    new_list = list()
    for entry in entries:
        if entry.get('visibility') == 'private':
            continue
        new_list.append(entry)
    return new_list


def filter_declined_entries(entries):

    new_list = list()

    for entry in entries:
        if entry.get('attendees'):
            me = [x for x in entry.get('attendees') if x.get('self') is True]
            if len(me) != 1:
                print 'length is not 1; something is weird'
            me = me[0]
            if me['responseStatus'] == 'declined':
                continue
        new_list.append(entry)

    return new_list


def filter_cancelled_events(entries):

    new_list = list()
    for entry in entries:
        if entry.get('status') == 'cancelled':
            continue
        new_list.append(entry)
    return new_list


def filter_no_end_date(entries):

    new_list = list()
    for entry in entries:
        if entry.get('end_date', None) is None:
            continue
        new_list.append(entry)
    return new_list


def transform_data(entries, calendar_name):

    new_list = list()

    for entry in entries:
        entry['source'] = 'calendar'
        entry['calendar_name'] = calendar_name
        entry['title'] = entry.get('summary')
        entry['key'] = entry.get('iCalUID')

        # get tag, if there is one
        for attendee in entry.get('attendees', list()):
            if attendee.get('email') == calendar_name:
                if 'comment' in attendee:
                    pattern = re.compile('.*#(\S+)', re.IGNORECASE)
                    match = pattern.match(attendee['comment'])
                    if match:
                        entry['tag'] = match.group(1)

        new_list.append(entry)

    return new_list


def transform_dates(calendar_item):

    start = get_date(calendar_item, 'start')
    calendar_item['start_date'] = str(start)
    end = get_date(calendar_item, 'end')
    calendar_item['end_date'] = str(end)
    duration = end - start
    duration = duration.total_seconds()
    calendar_item['seconds'] = duration

    return calendar_item


def process(calendar_entries, calendar_name):

    content = json.loads(calendar_entries)

    entry_list = [transform_dates(x) for x in content['items']]
    entry_list = filter_no_end_date(entry_list)
    entry_list = filter_cancelled_events(entry_list)
    entry_list = filter_private_entries(entry_list)
    entry_list = filter_declined_entries(entry_list)
    entry_list = transform_data(entry_list, calendar_name)

    return entry_list


def go(calendar_name):

    http = do_google_oauth_stuff()

    resp, content = http.request(
        "https://www.googleapis.com/calendar/v3/calendars/{}/"
        "events?orderBy=startTime&singleEvents=true&timeMax="
        "{}&timeMin={}".format(calendar_name, end_query, start_query), "GET")

    if resp.status != 200:
        print resp
        print resp.status
        print resp.content
        raise Exception
    bar = process(content, calendar_name)
    return bar


if __name__ == '__main__':

    config = ConfigObj(expanduser('~/.m6rc'))

    parser = argparse.ArgumentParser(
        description='fetch Google calendar entries and queue them')
    parsed = parser.parse_args()
    #foo = go(parsed.calendar)
    entries = go(config['google-calendar']['calendar'])
    print json.dumps(entries, indent=2)

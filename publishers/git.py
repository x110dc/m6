#!/usr/bin/env python

import collections
import datetime
import fnmatch
import json
import os
import os.path
import re
from os.path import expanduser

from configobj import ConfigObj
from sh import git

git = git.bake('--no-pager')

# this regex is intended to match strings like this:
# 4f994a3ff5dc62e01a5967f48c5883e60a53890f (remotes/svn/foobar~1)
# the first match should be the hash ref
# the second match should be the ref name without the trailing tilde and
# digits:
HASH_NAME_RE = re.compile(r'\b([0-9a-f]{40})\s\((.*?)(~\d+)?\)')


def list_of_local_repos(dirs):
    git_repos = list()
    for dir in dirs:
        for root, dirnames, filenames in os.walk(os.path.expanduser(dir)):
            for filename in fnmatch.filter(dirnames, '.git'):
                git_repos.append(os.path.join(root, filename))
    return git_repos


def log(repo, fields, author, days=7):

# idea borrowed from here for delimiters:
# http://blog.lost-theory.org/post/how-to-parse-git-log-output/
    log_format = '%x1f'.join(fields.values()) + '%x1e'
    date = datetime.date.today() - datetime.timedelta(days=days)
#    name_rev = git('--git-dir', repo, 'name-rev', '--stdin')
    try:
        if days == 0:
            command = git(git('--git-dir', repo, 'log', format=log_format,
                              author=author, all=True),
                          '--git-dir', repo, 'name-rev', '--stdin'
                          )
        else:
            command = git(git('--git-dir', repo, 'log',
                          after=date,
                          format=log_format,
                          author=author,
                          all=True),
                          '--git-dir', repo, 'name-rev', '--stdin'
                          )
    except Exception as e:
        # this is the error message if it's a newly created repo with
        # no commits. it doesn't seem to my like 'git log' should report
        # an error here.  Also this is brittle if the error message changes:
        if e.stderr == 'fatal: bad default revision \'HEAD\'\n':
            return list()
        raise e
    if command.stdout == '':
        return list()
    parsed = command.stdout.strip('\n\x1e').split("\x1e")
    parsed = [x.strip().split("\x1f") for x in parsed]
    # convert to a dictionary with field names as keys:
    log_entries = [dict(zip(fields.keys(), x)) for x in parsed]
    for entry in log_entries:
        # extract ref name and hash:
        matches = re.match(HASH_NAME_RE, entry['commit_hash'])
        entry['commit_hash'] = matches.group(1)
        entry['branch'] = os.path.basename(matches.group(2))
        entry['commit_message'] = entry['commit_message'].rstrip()
    return log_entries


def add_fields(entries, repo, config):

    description = open('{}/description'.format(repo), 'r').read().rstrip()

    repo_name = os.path.basename(repo.replace('/.git', ''))

    if not description.startswith('Unnamed repository'):
        repo_name = '{} ({})'.format(repo_name, description)

    # add the name of the repo:
    [x.setdefault('repo_name', repo_name) for x in entries]
    # add source:
    [x.setdefault('source', 'Git') for x in entries]
    # copy date:
    [x.setdefault('end_date', x['date']) for x in entries]
    # add a seconds field:
    [x.setdefault('seconds', int(config['duration'])) for x in entries]

    # make the 'key' be concat of repo name and branch:
    for entry in entries:
        entry['key'] = entry['repo_name'] + '/' + entry['branch']

    # copy commit message to notes list:
    [x.setdefault('notes', [x['commit_message']]) for x in entries]

    return entries


def go(config):

# define the fields of git-log output I want:
    fields = collections.OrderedDict()
    fields['author'] = '%ae'
    fields['branch'] = '%d'
    fields['date'] = '%ai'
    fields['commit_message'] = '%B'
    fields['commit_hash'] = '%H'

    local_repo_list = list_of_local_repos(config['repo_dirs'])
    entries = list()

    for repo in local_repo_list:
        # TODO: days=0 was added here so that a test would pass
        # for a pre-contructed git repo; instead a git repo
        # should be created on-the-fly for the test so that
        # we can only query 7 days here or some shorter period:
        log_entries = log(repo=repo, fields=fields, days=0,
                          author=config['author'])
        log_entries = add_fields(log_entries, repo, config)
        entries.extend(log_entries)

    return entries

if __name__ == '__main__':

    config = ConfigObj(expanduser('~/.m6rc'))

    entries = go(config['git'])

    print json.dumps(entries, indent=2)

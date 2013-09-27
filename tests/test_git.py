import collections
import tempfile
import unittest
from os.path import basename, split

import tempdir
from configobj import ConfigObj
from sh import git as gitsh

from publishers import git


def overwrite(file_object, text):
    if file_object.closed:
        file_object = open(file_object.name, 'w')
    file_object.write(text)
    file_object.close()


def test_git_repo():
    # create repo
    repo_dir = tempdir.TempDir()
    gitsh.init(repo_dir.name)
    # put something in the description file:
    description = open('{}/.git/description'.format(repo_dir.name), 'w')
    overwrite(description, 'Depeche Mode')
    # create a single file
    repo_file = tempfile.NamedTemporaryFile(dir=repo_dir.name, delete=False)
    overwrite(repo_file, '123\n')
    # commit it
    gitsh.add(repo_file.name, _cwd=repo_dir.name)
    gitsh.commit(m='message', author='First Last <first.last@a.com>',
                 _cwd=repo_dir.name)
    return repo_dir


def create_config(repo_path):

    config = ConfigObj()
    config['repo_dirs'] = [repo_path]
    return config.write()


class TestGit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.fields = collections.OrderedDict()
        cls.fields['author'] = '%ae'
        cls.fields['branch'] = '%d'
        cls.fields['date'] = '%ai'
        cls.fields['commit_hash'] = '%H'
        cls.fields['commit_message'] = '%B'

        cls.repo_path = test_git_repo()

        cls.git_repo_path = '{}/.git'.format(cls.repo_path.name)
        cls.repo_name = basename(cls.repo_path.name)

        cls.config = {'repo_dirs': [cls.repo_path.name],
                      'duration': 600,
                      'author': 'first.last',
                      }

    @classmethod
    def tearDownClass(cls):
        cls.repo_path.dissolve()

    def test_go(self):

        actual = git.go(self.config)
        self.assertEqual('master', actual[0]['branch'])
        expected = '{} (Depeche Mode)/master'.format(self.repo_name)
        self.assertEqual(expected, actual[0]['key'])
        expected = '{} (Depeche Mode)'.format(self.repo_name)
        self.assertEqual(expected, actual[0]['repo_name'])
        self.assertEqual(['message'], actual[0]['notes'])

    def test_list_of_local_repos(self):
        dir = split(split(self.git_repo_path)[0])[0]
        actual = git.list_of_local_repos([dir])
        expected = [self.git_repo_path]
        self.assertEqual(expected, actual)

    def test_git_log(self):

        # no commits, so it should be an empty list:
        out = git.log(repo=self.git_repo_path, days=0,
                      fields=self.fields, author='bogus')
        self.assertEqual([], out)

        actual = git.log(repo=self.git_repo_path, days=0,
                         fields=self.fields, author='first')
        self.assertEqual('message', actual[0]['commit_message'])
        self.assertEqual('master', actual[0]['branch'])

    def test_add_fields(self):
        entries = [{'author': 'foo.bar@example.com',
                    'branch': ' (HEAD, master)',
                    'commit_message': 'message',
                    'date': '2013-05-15 18:33:02 -0500'}]
        expected = [{'author': 'foo.bar@example.com',
                     'branch': ' (HEAD, master)',
                     'notes': ['message'],
                     'key': '{} (Depeche Mode)/ (HEAD, master)'.format(
                         self.repo_name),
                     'seconds': 600,
                     'commit_message': 'message',
                     'source': 'Git',
                     'repo_name': '{} (Depeche Mode)'.format(self.repo_name),
                     'end_date': '2013-05-15 18:33:02 -0500',
                     'date': '2013-05-15 18:33:02 -0500'}]
        actual = git.add_fields(entries, self.git_repo_path, self.config)
        self.assertEqual(expected, actual)

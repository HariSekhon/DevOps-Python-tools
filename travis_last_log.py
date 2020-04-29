#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-10 18:18:03 +0100 (Wed, 10 Aug 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to automate fetching the last running / completed / failed build log from Travis CI via the Travis API

By default fetches the latest build log even if currently executing

Options:

- fetch last completed build log
- fetch last failed build log

Also removes all control characters as while color coding is nice
there are a lot of other control sequences in Travis CI that mess terminals up

If specifying a --repo be aware the API is case sensitive for repo names

If repo starts with / and $TRAVIS_USER is set, will prepend $TRAVIS_USER for convenience, eg.

export TRAVIS_USER=HariSekhon # put this in .bashrc
travis_last_log.py /DevOps-Python-tools   # shorter to type than full 'HariSekhon/DevOps-Python-tools'

As a convenience you may supply either job id or repo as an argument without any switch and it'll infer it as a repo if
if contains a slash but no url (eg. HariSekhon/nagios-plugins) otherwise it'll assume it's a job id, strip any leading
URL so you can simply paste the path to a failing build and it'll just work. The switch versions of --job-id and --repo
take priority as they're more explicit

See also 'travis logs -r <repo>' from travis gem package. The main difference is this program can select the last
completed log or last failed log or a specific job id whereas with the 'travis logs' you only get the latest which might
still be executing. 'travis logs' is better for tailing the current build, whereas this program is better for quickly
checking the last error when your CCMenu or BuildNotify applet shows the last completed build failed

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# this breaks regex on Python 2.7 with UnicodeDecodeError traceback from the Travis CI output
#from __future__ import unicode_literals

import json
import logging
import os
import re
# not using string.printables now, more complex regex to strip ANSI control sequences now
#import string
import sys
import traceback
import git
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import prog, log, support_msg_api, jsonpp, qquit, isInt, isStr, isJson
    from harisekhon.utils import UnknownError, code_error, strip_ansi_escape_codes
    from harisekhon.utils import validate_chars, validate_alnum, validate_int
    from harisekhon import CLI
    from harisekhon import RequestHandler
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.1'


class TravisLastBuildLog(CLI):

    def __init__(self):
        # Python 2.x
        super(TravisLastBuildLog, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 600
        self.verbose_default = 1
        self.travis_token = None
        self.repo = None
        self.job_id = None
        self.num = None
        self.completed = False
        self.failed = False
        self.plaintext = False
        self.color = False
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Travis-API-Version': '3',
            'User-Agent': prog
        }
        self.request_handler = RequestHandler()

    def add_options(self):
        self.add_opt('-R', '--repo', default=os.getenv('TRAVIS_REPO'),
                     help='Travis CI repo to find last failed build ($TRAVIS_REPO)')
        self.add_opt('-J', '--job-id', default=os.getenv('TRAVIS_JOB_ID'),
                     help='Job ID to download log for a specific job ($TRAVIS_JOB_ID)')
        self.add_opt('-T', '--travis-token', default=os.getenv('TRAVIS_TOKEN'),
                     help='Travis token required to authenticate to the API ($TRAVIS_TOKEN)')
        self.add_opt('-n', '--num', default=1, help='Number of builds to pull logs from (default: 1)')
        self.add_opt('-c', '--completed', action='store_true', default=False, help='Only completed build(s)')
        self.add_opt('-f', '--failed', action='store_true', default=False, help='Only failed build(s)')
        #self.add_opt('-A', '--plaintext', action='store_true', default=False,
        #             help='Print in plaintext without fancy shell escapes ' + \
        #                  '(will do this by default if the output is not an interactive terminal ' + \
        #                  'such as piping through more)')
        #self.add_opt('-C', '--color', action='store_true', default=False,
        #             help='Force retention of fancy colour output regardless of interactive terminal or not ' + \
        #                  '(for piping through less -R)')

    def process_options(self):
        self.travis_token = self.get_opt('travis_token')
        self.repo = self.get_opt('repo')
        self.job_id = self.get_opt('job_id')
        if self.args:
            if '/' in self.args[0] and '://' not in self.args[0]:
                if not self.repo:
                    log.info('using argument as --repo')
                    self.repo = self.args[0]
            elif not self.job_id:
                log.info('using argument as --job-id')
                self.job_id = self.args[0]
        if self.job_id:
            # convenience to be able to lazily paste a URL like the following and still have it extract the job_id
            # https://travis-ci.org/HariSekhon/nagios-plugins/jobs/283840596#L1079
            self.job_id = self.job_id.split('/')[-1].split('#')[0]
            validate_chars(self.job_id, 'job id', '0-9')
        elif self.repo:
            travis_user = os.getenv('TRAVIS_USER')
            if '/' not in self.repo:
                self.repo = '/' + self.repo
            if self.repo[0] == '/' and travis_user:
                self.repo = travis_user + self.repo
            validate_chars(self.repo, 'repo', r'\/\w\.-')
        else:
            self.repo = self.get_local_repo_name()
            if not self.repo:
                self.usage('--job-id / --repo not specified')
        validate_alnum(self.travis_token, 'travis token', is_secret=True)
        self.headers['Authorization'] = 'token {0}'.format(self.travis_token)
        self.num = self.get_opt('num')
        validate_int(self.num, 'num', 1)
        self.num = int(self.num)
        self.completed = self.get_opt('completed')
        self.failed = self.get_opt('failed')
        #self.plaintext = self.get_opt('plaintext')
        #self.color = self.get_opt('color')
        #if self.plaintext and self.color:
        #    self.usage('cannot specify --plaintext and --color at the same time, they are mutually exclusive!')
        # test for interactive, switch off color if piping stdout somewhere
        #if not self.color and not (sys.__stdin__.isatty() and sys.__stdout__.isatty()):
        #    self.plaintext = True

    @staticmethod
    def get_local_repo_name():
        try:
            _ = git.Repo('.')
            for remote in _.remotes:
                for url in remote.urls:
                    repo = '/'.join(url.split('/')[-2:])
                    log.debug('determined repo to be {} from remotes'.format(repo))
                    return repo
        except git.InvalidGitRepositoryError:
            log.debug('failed to determine git repository locally: %s', _)

    def run(self):
        if self.job_id:
            self.print_log(job_id=self.job_id)
        else:
            builds = self.get_builds()
            for build in builds:
                self.print_log(build=build)

    @staticmethod
    def parse_travis_error(req):
        error_message = ''
        try:
            _ = json.loads(req.content)
            error_message = _['error_message']
        except ValueError:
            if isStr(req.content) and len(req.content.split('\n')) == 1:
                error_message = req.content
        return error_message

    def get_builds(self):
        builds = self.get_latest_builds()
        try:
            builds = self.parse_builds(builds)
        except (KeyError, ValueError):
            exception = traceback.format_exc().split('\n')[-2]
            # this covers up the traceback info and makes it harder to debug
            #raise UnknownError('failed to parse expected json response from Travis CI API: {0}'.format(exception))
            qquit('UNKNOWN', 'failed to parse expected json response from Travis CI API: {0}. {1}'.
                  format(exception, support_msg_api()))
        return builds

    def get_latest_builds(self):
        log.info('getting latest builds')
        # gets 404 unless replacing the slash
        url = 'https://api.travis-ci.org/repo/{repo}/builds'.format(repo=self.repo.replace('/', '%2F'))
        # request returns blank without authorization header
        req = self.request_handler.get(url, headers=self.headers)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("\n%s", jsonpp(req.content))
        if not isJson(req.content):
            raise UnknownError('non-json returned by Travis CI. {0}'.format(support_msg_api()))
        return req.content

    def parse_builds(self, content):
        log.debug('parsing build info')
        build = None
        collected_builds = []
        json_data = json.loads(content)
        if not json_data or \
           'builds' not in json_data or \
           not json_data['builds']:
            qquit('UNKNOWN', "no Travis CI builds returned by the Travis API."
                  + " Either the specified repo '{0}' doesn't exist".format(self.repo)
                  + " or no builds have happened yet?"
                  + " Also remember the repo is case sensitive, for example 'harisekhon/nagios-plugins' returns this"
                  + " blank build set whereas 'HariSekhon/Nagios-Plugins' succeeds"
                  + " in returning latest builds information"
                 )
        builds = json_data['builds']
        # get latest finished failed build
        last_build_number = None
        found_newer_passing_build = False
        for _ in builds:
            # API returns most recent build first
            # extra check to make sure we're getting the very latest build number and API hasn't changed
            build_number = _['number']
            if not isInt(build_number):
                raise UnknownError('build number returned is not an integer!')
            build_number = int(build_number)
            if last_build_number is None:
                last_build_number = int(build_number) + 1
            if build_number >= last_build_number:
                raise UnknownError('build number returned is out of sequence, cannot be >= last build returned' + \
                                   '{0}'.format(support_msg_api()))
            last_build_number = build_number
            if self.completed:
                if len(collected_builds) < self.num and _['state'] in ('passed', 'finished', 'failed', 'errored'):
                    collected_builds.append(_)
            elif self.failed:
                if _['state'] == 'passed':
                    if not collected_builds and not found_newer_passing_build:
                        log.warning("found more recent successful build #%s with state = '%s'" + \
                                    ", you may not need to debug this build any more", _['number'], _['state'])
                        found_newer_passing_build = True
                elif _['state'] in ('failed', 'errored'):
                    if len(collected_builds) < self.num:
                        collected_builds.append(_)
                        # by continuing to iterate through the rest of the builds we can check
                        # their last_build numbers are descending for extra sanity checking
                        #break
            elif len(collected_builds) < self.num:
                collected_builds.append(_)
                # by continuing to iterate through the rest of the builds we can check
                # their last_build numbers are descending for extra sanity checking
                #break
        if not collected_builds:
            qquit('UNKNOWN', 'no recent builds found')
        if log.isEnabledFor(logging.DEBUG):
            for build in collected_builds:
                log.debug("build:\n%s", jsonpp(build))
        return collected_builds

    def print_log(self, build=None, job_id=None):
        if job_id:
            self.print_job_log(job_id=job_id)
            log.info('=' * 80)
            log.info('end of log for job id %s', job_id)
            log.info('=' * 80 + '\n')
        else:
            if not build:
                code_error('no job id passed to print_log(), nor build to determine job from')
            log.info('getting job id for build #%s', build['number'])
            if 'jobs' not in build:
                raise UnknownError('no jobs field found in build, {0}'.format(support_msg_api))
            for _ in build['jobs']:
                _id = _['id']
                url = 'https://api.travis-ci.org/jobs/{id}'.format(id=_id)
                req = self.request_handler.get(url)
                # if this raises ValueError it'll be caught by run handler
                job_data = json.loads(req.content)
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("job id %s status:\n%s", _id, jsonpp(job_data))
                if self.failed is True:
                    if job_data['state'] == 'finished' and job_data['status'] in (None, 1, '1'):
                        job = job_data
                else:
                    job = job_data
            if not job:
                raise UnknownError('no job found in build {0}'.format(build['number']))
            self.print_job_log(job=job)
            log.info('=' * 80)
            log.info('end of log for build number #%s job id %s', build['number'], job['id'])
            log.info('=' * 80 + '\n')

    def print_job_log(self, job=None, job_id=None):
        #if (self.color or not self.plaintext) and 'log' in job:
        if not job and not job_id:
            code_error('no job data or job id passed to print_job_log()')
        content = None
        if job is not None:
            if 'log' in job and job['log']:
                content = job['log']
            else:
                job_id = job['id']
        if not content:
            url = 'https://api.travis-ci.org/jobs/{id}/log.txt?deansi=true'.format(id=job_id)
            req = self.request_handler.get(url)
            content = req.content
        content = re.sub(r'\r', '', content)
        #if self.plaintext:
            # leaves a few characters behind which are printable
            #content = re.sub('[^{0}]'.format(string.printable), '', content)
        # mandatory stripping ANSI control sequences for now as although color coding is nice
        # Travis has too many other control sequences that mess up my terminal
        # strip all control sequences
        content = strip_ansi_escape_codes(content)
        print(content)


if __name__ == '__main__':
    TravisLastBuildLog().main()

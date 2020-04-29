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

Tool to automate initiating a Travis CI interactive debug build session via the Travis API

Tracks the creation of the debug build and drops you in to an SSH shell as soon as it's available

If you get an access denied error but are sure your Travis API token is correct then it could be because the repo hasn't
been enabled for debugging yet (you may need to contact Travis at support@travis-ci.com for them to enable it for you)

If specifying a --repo be aware the API is case sensitive for repo names

As a convenience you may supply either job id or repo as an argument without any switch and it'll infer it as a repo if
if contains a slash but no url (eg. HariSekhon/Nagios-Plugins) otherwise it'll assume it's a job id, strip any leading
URL so you can simply paste the path to a failing build and it'll just work. The switch versions of --job-id and --repo
take priority as they're more explicit

Travis CI doc on debug builds:

    https://docs.travis-ci.com/user/running-build-in-debug-mode/

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import json
import logging
import os
import re
import sys
import time
import traceback
import git
try:
    import requests
except ImportError:
    print(traceback.format_exc(), end='')
    sys.exit(4)
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import prog, log, support_msg_api, jsonpp, qquit, isInt, isStr
    from harisekhon.utils import CriticalError, UnknownError, code_error
    from harisekhon.utils import validate_chars, validate_alnum, host_regex
    from harisekhon import CLI
    from harisekhon import RequestHandler
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.9.1'


class TravisDebugSession(CLI):

    def __init__(self):
        # Python 2.x
        super(TravisDebugSession, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 600
        self.verbose_default = 2
        self.job_id = None
        self.travis_token = None
        self.repo = None
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Travis-API-Version': '3',
            'User-Agent': prog
        }
        self.request_handler = RequestHandler()

    def check_job_launch_response_code(self, req):
        if req.status_code == 409:
            error_message = self.parse_travis_error(req)
            error_message += " (if you've just retriggered this you can avoid this error " + \
                             "using the --ignore-running switch)"
            if self.get_opt('ignore_running'):
                log.info('job already running (ignoring)')
            else:
                log.info('job already running')
                raise CriticalError('{0} {1}: {2}'.format(req.status_code, req.reason, error_message))
        elif req.status_code != 202:
            error_message = self.parse_travis_error(req)
            raise CriticalError("{0} {1}: {2}".format(req.status_code, req.reason, error_message))

    def add_options(self):
        self.add_opt('-J', '--job-id', default=os.getenv('JOB_ID'),
                     help='Travis Job ID to initiate the debug session ($JOB_ID)')
        self.add_opt('-T', '--travis-token', default=os.getenv('TRAVIS_TOKEN'),
                     help='Travis token required to authenticate to the API ($TRAVIS_TOKEN)')
        self.add_opt('-R', '--repo', default=os.getenv('TRAVIS_REPO'),
                     help='Travis CI repo to find last failed build and re-execute a job from it ($TRAVIS_REPO)' + \
                          ', easier alternative to specifying a specific --job-id' + \
                          ', convenient if working with the same repo over and over and don\'t want to copy the ' + \
                          'job id each time (--job-id takes priority if given as it\'s more specific). ' + \
                          'Be aware if running this quickly in succession you will get older and older failed ' + \
                          'builds as the last one will still be running, will only re-trigger finished failed builds')
        self.add_opt('-i', '--ignore-running', action='store_true',
                     help='Ignore job already running error (avoids 409 error if you try to restart debug job)')

    def process_options(self):
        self.job_id = self.get_opt('job_id')
        self.travis_token = self.get_opt('travis_token')
        self.repo = self.get_opt('repo')
        #if travis_token is None:
        #    self.usage('--travis-token option or ' +
        #               '$TRAVIS_TOKEN environment variable required to authenticate to the API')
        if self.args:
            # assume arg is a repo in form of HariSekhon/Nagios-Plugins but do not use url which we are more likely to
            # have pasted a travis-ci url to a job, see a few lines further down
            if '/' in self.args[0]:
                if not self.repo:
                    log.info('using argument as --repo')
                    self.repo = self.args[0]
            elif not self.job_id:
                log.info('using argument as --job-id')
                self.job_id = self.args[0]
        if self.job_id:
            # convenience to be able to lazily paste a URL like the following and still have it extract the job_id
            # https://travis-ci.org/HariSekhon/Nagios-Plugins/jobs/283840596#L1079
            self.job_id = self.job_id.split('/')[-1].split('#')[0]
            validate_chars(self.job_id, 'job id', '0-9')
        elif self.repo:
            self.repo = re.sub(r'https?://travis-ci\.org/', '', self.repo)
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
        if not self.job_id:
            if self.repo:
                latest_failed_build = self.get_latest_failed_build()
                self.job_id = self.get_failing_job_id_from_build(latest_failed_build)
            else:
                code_error('--job-id / --repo not specified, caught late')

        if self.job_id is None:
            raise UnknownError('no job id was found, aborting getting SSH address')
        self.launch_job()
        ssh_address = self.get_ssh_address(job_id=self.job_id)
        log.info('Executing: ssh -- {0}'.format(ssh_address))
        sys.stdout.flush()
        sys.stderr.flush()
        self.disable_timeout()
        os.execvp('ssh', ['--', ssh_address])

    def launch_job(self):
        log.info('triggering debug job {job_id}'.format(job_id=self.job_id))
        url = 'https://api.travis-ci.org/job/{job_id}/debug'.format(job_id=self.job_id)
        self.request_handler.check_response_code = self.check_job_launch_response_code
        self.request_handler.post(url, headers=self.headers)

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

    def get_latest_failed_build(self):
        log.info('getting latest failed build')
        # gets 404 unless replacing the slash
        url = 'https://api.travis-ci.org/repo/{repo}/builds'.format(repo=self.repo.replace('/', '%2F'))
        # request returns blank without authorization header
        req = self.request_handler.get(url, headers=self.headers)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("\n%s", jsonpp(req.content))
        try:
            latest_build = self.parse_latest_failed_build(req.content)
        except (KeyError, ValueError):
            exception = traceback.format_exc().split('\n')[-2]
            # this covers up the traceback info and makes it harder to debug
            #raise UnknownError('failed to parse expected json response from Travis CI API: {0}'.format(exception))
            qquit('UNKNOWN', 'failed to parse expected json response from Travis CI API: {0}. {1}'.
                  format(exception, support_msg_api()))
        return latest_build

    def parse_latest_failed_build(self, content):
        log.debug('parsing latest failed build info')
        build = None
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
            # API returns most recent build first so just take the first one that is completed
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
            if _['state'] == 'passed':
                if build is None and not found_newer_passing_build:
                    log.warning("found more recent successful build #%s with state = '%s'" + \
                                ", you may not need to debug this build any more", _['number'], _['state'])
                    found_newer_passing_build = True
            elif _['state'] in ('failed', 'errored'):
                if build is None:
                    build = _
                    # by continuing to iterate through the rest of the builds we can check
                    # their last_build numbers are descending for extra sanity checking
                    #break
        if build is None:
            qquit('UNKNOWN', 'no recent failed builds found' + \
                             ', you may need to specify the --job-id explicitly as shown in the Travis CI UI')
        if log.isEnabledFor(logging.DEBUG):
            log.debug("latest failed build:\n%s", jsonpp(build))
        return build

    def get_failing_job_id_from_build(self, build):
        log.info('getting failed job id for build #%s', build['number'])
        if 'jobs' not in build:
            raise UnknownError('no jobs field found in build, {0}'.format(support_msg_api))
        for _ in build['jobs']:
            _id = _['id']
            url = 'https://api.travis-ci.org/jobs/{id}'.format(id=_id)
            req = self.request_handler.get(url)
            # if this raises ValueError it'll be caught by run handler
            job = json.loads(req.content)
            if log.isEnabledFor(logging.DEBUG):
                log.debug("job id %s status:\n%s", _id, jsonpp(job))
            if job['state'] == 'finished' and job['status'] in (None, 1, '1'):
                return _id
        raise UnknownError('no failed job found in build {0}'.format(build['number']))

    def get_ssh_address(self, job_id):
        log.info('getting SSH address from triggered debug build')
        max_tries = int(self.timeout / 4)
        for i in range(1, max_tries + 1):
            log.info('try {0}/{1}: checking job log for ssh address...'.format(i, max_tries))
            ssh_address = self.get_ssh_address_attempt(job_id=job_id)
            if ssh_address:
                return ssh_address
            time.sleep(3)
        if ssh_address is None:
            raise CriticalError('ssh address not found in output from Travis API. {0}'.format(support_msg_api()))

    def get_ssh_address_attempt(self, job_id):
        #url = 'https://travis-ci.org/{repo}/jobs/{job_id}'.format(repo=repo, job_id=job_id)
        url = 'https://api.travis-ci.org/jobs/{job_id}/log.txt?deansi=true'.format(job_id=job_id)
        log.debug('GET %s' % url)
        try:
            req = requests.get(url)
        except requests.exceptions.RequestException as _:
            raise CriticalError(_)
        log.debug("response: %s %s", req.status_code, req.reason)
        log.debug("content:\n%s\n%s\n%s", '=' * 80, req.content.strip(), '=' * 80)
        # Travis CI behaviour has changed from 200 with no content indicating build log empty, not started yet
        # to now returning "500 Internal Server Error", content: "Sorry, we experienced an error."
        if req.status_code == 500:
            # don't output 500 it will confuse users in to thinking there is a real error which 500 usually indicates
            #log.info('500 internal server error, build not started yet')
            log.info('build not started yet')
            return None
        if req.status_code != 200:
            error_message = self.parse_travis_error(req)
            raise CriticalError('{0} {1}: {2}'.format(req.status_code, req.reason, error_message))
        content = req.content
        if not content:
            log.info('build log empty, build not started yet')
            return None
        # find last non-blank line - do this after checking for no content otherwise will hit StopIteration
        last_line = next(_ for _ in reversed(content.split('\n')) if _)
        #log.debug('last line: %s', last_line)
        # 'Done: Job Cancelled'
        if 'Job Cancelled' in last_line:
            raise CriticalError(last_line)
        elif 'Your build has been stopped' in last_line:
            raise CriticalError(last_line)
        # Done. Your build exited with 0
        elif 'build exited with' in last_line:
            raise CriticalError(last_line)
        # The build has been terminated
        elif 'build has been terminated' in last_line:
            raise CriticalError(last_line)

        ssh_address = None
        regex_ssh = re.compile(r'^\s*ssh\s+(\w+\@{host_regex})\s*$'.format(host_regex=host_regex), re.I)
        for line in content.split('\n'):
            match = regex_ssh.match(line)
            if match:
                ssh_address = match.group(1)
                break
        return ssh_address


if __name__ == '__main__':
    TravisDebugSession().main()

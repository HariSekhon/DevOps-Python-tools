#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-10 18:18:03 +0100 (Wed, 10 Aug 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to automate initiating a Travis CI interactive debug build session

Tracks the creation of the debug build and drops you in to an SSH shell as soon as it's available

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import json
import os
import re
import sys
import time
import traceback
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
    from harisekhon.utils import log, support_msg_api
    from harisekhon.utils import CriticalError
    from harisekhon.utils import validate_chars, validate_alnum, host_regex
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2'


class TravisDebugSession(CLI):

    def __init__(self):
        # Python 2.x
        super(TravisDebugSession, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 600
        self.verbose_default = 2

    def add_options(self):
        self.add_opt('-J', '--job-id',
                     help='Travis Job ID to initiate the debug session ($JOB_ID)')
        self.add_opt('-T', '--travis-token',
                     help='Travis token required to authenticate to the API ($TRAVIS_TOKEN)')
        self.add_opt('-i', '--ignore-running', action='store_true',
                     help='Ignore job already running error (avoids 409 error if you try to restart debug job)')

    def run(self):
        job_id = self.get_opt('job_id')
        travis_token = self.get_opt('travis_token')
        if job_id is None:
            travis_token = os.getenv('JOB_ID')
        if travis_token is None:
            travis_token = os.getenv('TRAVIS_TOKEN')
        #if travis_token is None:
        #    self.usage('--travis-token option or ' +
        #               '$TRAVIS_TOKEN environment variable required to authenticate to the API')
        validate_chars(job_id, 'job id', '0-9')
        validate_alnum(travis_token, 'travis token')

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Travis-API-Version': '3',
            'Authorization': 'token {0}'.format(travis_token)
        }
        log.info('triggering debug job {job_id}'.format(job_id=job_id))
        url = 'https://api.travis-ci.org/job/{job_id}/debug'.format(job_id=job_id)
        log.debug('POST %s' % url)
        try:
            req = requests.post(url, headers=headers)
        except requests.exceptions.RequestException as _:
            raise CriticalError(_)
        log.debug("response: %s %s", req.status_code, req.reason)
        log.debug("content:\n%s\n%s\n%s", '='*80, req.content.strip(), '='*80)
        if req.status_code == 409:
            error_message = ''
            try:
                _ = json.loads(req.content)
                error_message = _['error_message']
            except ValueError:
                pass
            error_message += " (if you've just retriggered this you can avoid this error using the --ignore-running switch)"
            if self.get_opt('ignore_running'):
                log.info('job already running (ignoring)')
            else:
                log.info('job already running')
                raise CriticalError('{0} {1}: {2}'.format(req.status_code, req.reason, error_message))
        elif req.status_code != 202:
            raise CriticalError("%s %s" % (req.status_code, req.reason))

        # don't need to query this if using the API address rather than the web UI address
        # as we don't need to figure out the repo name, just use the job id by itself
#        url = 'https://api.travis-ci.org/job/{job_id}'.format(job_id=job_id)
#        log.debug('GET %s' % url)
#        try:
#            req = requests.get(url, headers=headers)
#        except requests.exceptions.RequestException as _:
#            raise CriticalError(_)
#        log.debug("response: %s %s", req.status_code, req.reason)
#        log.debug("content:\n%s\n%s\n%s", '='*80, req.content.strip(), '='*80)
#        if req.status_code != 200:
#            raise CriticalError("%s %s" % (req.status_code, req.reason))
#
#        repo = None
#        try:
#            repo = json.loads(req.content)['repository']['slug']
#        except ValueError as _:
#            raise

        ssh_address = self.get_ssh_address(job_id=job_id)
        log.info('Executing: ssh -- {0}'.format(ssh_address))
        sys.stdout.flush()
        sys.stderr.flush()
        self.disable_timeout()
        os.execvp('ssh', ['--', ssh_address])

    @staticmethod
    def get_ssh_address_attempt(job_id):
        #url = 'https://travis-ci.org/{repo}/jobs/{job_id}'.format(repo=repo, job_id=job_id)
        url = 'https://api.travis-ci.org/jobs/{job_id}/log.txt?deansi=true'.format(job_id=job_id)
        log.debug('GET %s' % url)
        try:
            req = requests.get(url)
        except requests.exceptions.RequestException as _:
            raise CriticalError(_)
        log.debug("response: %s %s", req.status_code, req.reason)
        log.debug("content:\n%s\n%s\n%s", '='*80, req.content.strip(), '='*80)
        if req.status_code != 200:
            raise CriticalError("%s %s" % (req.status_code, req.reason))

        ssh_address = None
        regex_ssh = re.compile(r'^ssh\s+(\w+\@{host_regex})\s*$'.format(host_regex=host_regex))
        for line in req.content.split('\n'):
            match = regex_ssh.match(line)
            if match:
                ssh_address = match.group(1)
                break
        return ssh_address

    def get_ssh_address(self, job_id):
        max_tries = int(self.timeout / 4)
        for i in range(1, max_tries + 1):
            log.info('try {0}/{1}: checking job log for ssh address...'.format(i, max_tries))
            ssh_address = self.get_ssh_address_attempt(job_id=job_id)
            if ssh_address:
                return ssh_address
            time.sleep(3)
        if ssh_address is None:
            raise CriticalError('ssh address not found in output from Travis API. {0}'.format(support_msg_api()))


if __name__ == '__main__':
    TravisDebugSession().main()

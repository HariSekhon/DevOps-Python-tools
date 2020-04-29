#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-12-16 11:37:15 +0000 (Mon, 16 Dec 2019)
#
#  https://github.com/harisekhon/nagios-plugins
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Find AWS IAM user accounts last used age in days using the most recently used among their timestamp and access keys

Optionally filters to only users > N days old to find old user accounts

Generates an IAM credential report, then parses it to determine the time since each user's password
and access keys were last used

Requires iam:GenerateCredentialReport on resource: *

Output:

<user>  <days_since_used>   <password_last_used_date>  <access_key_1_last_used_date> <access_key_2_last_used_date>

Uses the Boto python library, read here for the list of ways to configure your AWS credentials:

    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html

See also the DevOps Bash Tools and Advanced Nagios Plugins Collection repos which have more similar AWS tools

- https://github.com/harisekhon/devops-bash-tools
- https://github.com/harisekhon/nagios-plugins

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import csv
import os
import sys
import time
import traceback
from datetime import datetime
from io import StringIO
from math import floor
import boto3
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1.1'


class AWSUsersLastUsed(CLI):

    def __init__(self):
        # Python 2.x
        super(AWSUsersLastUsed, self).__init__()
        # Python 3.x
        # super().__init__()
        self.age = None
        self.now = None
        self.timeout_default = 300
        self.msg = 'AWSUsersLastUsed msg not defined'

    def add_options(self):
        self.add_opt('-a', '--age', type=float,
                     help='Filters to show only accounts last used more than N days ago')

    def process_args(self):
        self.no_args()
        self.age = self.get_opt('age')
        if self.age is not None:
            validate_int(self.age, 'age')

    def run(self):
        iam = boto3.client('iam')
        log.info('generating credentials report')
        while True:
            result = iam.generate_credential_report()
            log.debug('%s', result)
            if result['State'] == 'COMPLETE':
                log.info('credentials report generated')
                break
            log.info('waiting for credentials report')
            time.sleep(1)
        #try:
        result = iam.get_credential_report()
        #except ClientError as _:
        #    raise
        csv_content = result['Content']
        log.debug('%s', csv_content)
        filehandle = StringIO(unicode(csv_content))
        filehandle.seek(0)
        csvreader = csv.reader(filehandle)
        headers = next(csvreader)
        assert headers[0] == 'user'
        assert headers[4] == 'password_last_used'
        assert headers[10] == 'access_key_1_last_used_date'
        assert headers[15] == 'access_key_2_last_used_date'
        self.now = datetime.utcnow()
        for row in csvreader:
            self.process_user(row)

    def process_user(self, row):
        log.debug('processing user: %s', row)
        user = row[0]
        password_last_used = row[4]
        access_key_1_last_used_date = row[10]
        access_key_2_last_used_date = row[15]
        log.debug('user: %s, password_last_used: %s, access_key_1_last_used_date: %s, access_key_2_last_used_date: %s',
                  user, password_last_used, access_key_1_last_used_date, access_key_2_last_used_date)
        min_age = None
        for _ in [password_last_used, access_key_1_last_used_date, access_key_2_last_used_date]:
            if _ == 'N/A':
                continue
            # %z not working in Python 2.7 but we already know it's +00:00
            _datetime = datetime.strptime(_.split('+')[0], '%Y-%m-%dT%H:%M:%S')
            age_timedelta = self.now - _datetime.replace(tzinfo=None)
            age_days = int(floor(age_timedelta.total_seconds() / 86400.0))
            if min_age is None or age_days < min_age:
                min_age = age_days
        if self.age and min_age <= self.age:
            return
        print('{user:20}\t{days:>3}\t{password_last_used:25}\t'\
              .format(user=user,
                      days=min_age,
                      password_last_used=password_last_used) +
              '{access_key_1_last_used_date:25}\t{access_key_2_last_used_date:25}'\
              .format(access_key_1_last_used_date=access_key_1_last_used_date,
                      access_key_2_last_used_date=access_key_2_last_used_date))


if __name__ == '__main__':
    AWSUsersLastUsed().main()

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

Find AWS IAM user access keys that haven't been used in N days and keys that have never been used

Generates an IAM credential report, then parses it to determine the time since each user's password
and access keys were last used

Requires iam:GenerateCredentialReport on resource: *

Output:

<user>  <access_key_num>  <status>  <unused_days>  <last_used_date>  <created_date>

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
from botocore.exceptions import ClientError
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
__version__ = '0.2.1'


class AWSUnusedAccessKeys(CLI):

    def __init__(self):
        # Python 2.x
        super(AWSUnusedAccessKeys, self).__init__()
        # Python 3.x
        # super().__init__()
        self.age = None
        self.now = None
        self.only_active = False
        self.timeout_default = 300
        self.msg = 'AWSUnusedAccessKeys msg not defined'

    def add_options(self):
        self.add_opt('-a', '--age', type=float, default=30,
                     help='Show only access keys not used in the last N days (default: 30)')
        self.add_opt('-o', '--only-active', action='store_true',
                     help='Only show access keys that are active')

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
        try:
            result = iam.get_credential_report()
        except ClientError as _:
            raise
        csv_content = result['Content']
        log.debug('%s', csv_content)
        filehandle = StringIO(unicode(csv_content))
        filehandle.seek(0)
        csvreader = csv.reader(filehandle)
        headers = next(csvreader)
        log.debug('headers: %s', headers)
        assert headers[0] == 'user'
        assert headers[8] == 'access_key_1_active'
        assert headers[9] == 'access_key_1_last_rotated'
        assert headers[10] == 'access_key_1_last_used_date'
        assert headers[13] == 'access_key_2_active'
        assert headers[14] == 'access_key_2_last_rotated'
        assert headers[15] == 'access_key_2_last_used_date'
        self.now = datetime.utcnow()
        for row in csvreader:
            self.process_user(row)

    def process_user(self, row):
        log.debug('processing user: %s', row)
        user = row[0]
        access_keys = {1:{}, 2:{}}
        access_keys[1]['active'] = row[8]
        access_keys[1]['last_used_date'] = row[10]
        access_keys[1]['last_rotated'] = row[9]
        access_keys[2]['active'] = row[13]
        access_keys[2]['last_rotated'] = row[14]
        access_keys[2]['last_used_date'] = row[15]
        for key in [1, 2]:
            active = access_keys[key]['active']
            if not isinstance(active, bool):
                assert active in ('true', 'false')
                active = active.lower() == 'true'
            created = access_keys[key]['last_rotated']
            last_used = access_keys[key]['last_used_date']
            log.debug('user: %s, key: %s, active: %s, created: %s, last_used_date: %s, ',
                      user,
                      key,
                      active,
                      created,
                      last_used
                     )
            if not active and self.only_active:
                continue
            if last_used == 'N/A':
                if created == 'N/A':
                    continue
                self.print_key(user, key, active, 'N/A', last_used, created)
                continue
            # %z not working in Python 2.7 but we already know it's +00:00
            _datetime = datetime.strptime(last_used.split('+')[0], '%Y-%m-%dT%H:%M:%S')
            age_timedelta = self.now - _datetime.replace(tzinfo=None)
            age_days = int(floor(age_timedelta.total_seconds() / 86400.0))
            if age_days > self.age:
                self.print_key(user, key, active, age_days, last_used, created)

    # pylint: disable=too-many-arguments
    def print_key(self, user, key, active, age_days, last_used, created):
        log.debug('access key %s, active: %s, last used %s days ago > %s', key, active, age_days, self.age)
        print('{user:20}\t{key}\t{active}\t{days:>3}\t{last_used:25}\t{created}'\
              .format(user=user,
                      key=key,
                      active='Active' if active else 'Inactive',
                      days=age_days,
                      last_used=last_used,
                      created=created
                     )
             )


if __name__ == '__main__':
    AWSUnusedAccessKeys().main()

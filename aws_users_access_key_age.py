#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-12-13 17:24:40 +0000 (Fri, 13 Dec 2019)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Lists all AWS IAM users keys along with their ages, optionally filtering any older than a given number of days

Output format is:

<user>      <status>    <created_date>

Status is usually Active

See also:

aws_users_access_key_age.sh - similar version in the adjacent DevOps Bash Tools repo
- https://github.com/harisekhon/devops-bash-tools

This version adds date parsing for finding keys older than a given time for enforcing periodic key rotation policies

Advanced Nagios Plugins (https://github.com/harisekhon/nagios-plugins)

check_aws_access_keys_age.py
check_aws_access_keys_disabled.py

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import os
import sys
import boto3
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, validate_float
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2.0'

class AWSUsersAccessKeysAge(CLI):

    def __init__(self):
        super(AWSUsersAccessKeysAge, self).__init__()
        self.age = None
        self.now = None
        self.only_active_keys = False
        self.timeout_default = 300

    def add_options(self):
        self.add_opt('-a', '--age', help='Return keys older than N days')
        self.add_opt('-o', '--only-active', action='store_true', help='Return only keys with Active status')

    def process_args(self):
        self.only_active_keys = self.get_opt('only_active')
        self.age = self.get_opt('age')
        if self.age:
            validate_float(self.age, 'age')
            self.age = float(self.age)
            self.age = self.age * 86400

    def run(self):
        iam = boto3.client('iam')
        user_paginator = iam.get_paginator('list_users')
        self.now = datetime.datetime.utcnow()
        for users_response in user_paginator.paginate():
            for user_item in users_response['Users']:
                username = user_item['UserName']
                key_paginator = iam.get_paginator('list_access_keys')
                for keys_response in key_paginator.paginate(UserName=username):
                    self.process_key(keys_response, username)
        log.info('Completed')

    def process_key(self, keys_response, username):
        #assert not keys_response['IsTruncated']
        for access_key_item in keys_response['AccessKeyMetadata']:
            assert username == access_key_item['UserName']
            status = access_key_item['Status']
            if self.only_active_keys and status != 'Active':
                continue
            create_date = access_key_item['CreateDate']
            if self.age:
                # already cast to datetime.datetime with tzinfo
                #create_datetime = datetime.datetime.strptime(create_date, '%Y-%m-%d %H:%M:%S%z')
                # removing tzinfo for comparison to avoid below error
                # - both are UTC and this doesn't make much difference anyway
                # TypeError: can't subtract offset-naive and offset-aware datetimes
                if (self.now - create_date.replace(tzinfo=None)).total_seconds() < self.age:
                    continue
            print('{user:20}\t{status}\t{date}'.format(
                user=username,
                status=status,
                date=create_date))


if __name__ == '__main__':
    AWSUsersAccessKeysAge().main()

#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-12-19 11:43:25 +0000 (Thu, 19 Dec 2019)
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

Lists all AWS IAM users dates since their passwords were last used, optionally filtering
for users whose passwords haven't been used in > N days

Output format is:

<user>      <pw_last_used_date>     <days_since_use>

Uses Boto, read here for the list of ways to configure your AWS credentials:

    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html

This version adds date parsing for finding keys older than a given time for enforcing periodic key rotation policies

See also the DevOps Bash Tools repo and The Advanced Nagios Plugins Collection for similar tools

https://github.com/harisekhon/devops-bash-tools

https://github.com/harisekhon/nagios-plugins

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import os
import sys
from math import floor
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
__version__ = '0.1.0'

class AWSUsersPasswordLastUsed(CLI):

    def __init__(self):
        super(AWSUsersPasswordLastUsed, self).__init__()
        self.age = None
        self.now = None
        self.timeout_default = 300

    def add_options(self):
        self.add_opt('-a', '--age', help='Return users with passwords last used more than N days ago')

    def process_args(self):
        self.age = self.get_opt('age')
        if self.age:
            validate_float(self.age, 'age')
            self.age = float(self.age)

    def run(self):
        iam = boto3.client('iam')
        user_paginator = iam.get_paginator('list_users')
        self.now = datetime.datetime.utcnow()
        for users_response in user_paginator.paginate():
            for user_item in users_response['Users']:
                log.debug(user_item)
                self.process_password_last_used(user_item)
        log.info('Completed')

    def process_password_last_used(self, user_item):
        # already cast to datetime.datetime with tzinfo
        user = user_item['UserName']
        if 'PasswordLastUsed' in user_item:
            password_last_used = user_item['PasswordLastUsed']
            # removing tzinfo for comparison to avoid below error
            # - both are UTC and this doesn't make much difference anyway
            # TypeError: can't subtract offset-naive and offset-aware datetimes
            datetime_delta = self.now - password_last_used.replace(tzinfo=None)
            days = int(floor(datetime_delta.total_seconds() / 86400))
            if self.age and days <= self.age:
                return
        else:
            password_last_used = 'N/A'
            days = 'N/A'
        print('{user:20s}\t{password_last_used:25s}\t({days:>3} days)'.format(
            user=user,
            password_last_used=str(password_last_used),  # without str() format string breaks with :25
            days=days))


if __name__ == '__main__':
    AWSUsersPasswordLastUsed().main()

#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-10-29 18:02:14 +0000 (Thu, 29 Oct 2020)
#
#  https://github.com/HariSekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/HariSekhon
#

"""

Lists all service account credential keys in a given GCP project

Excludes built-in system managed keys which are hidden in the Console UI anyway and are not actionable
or in scope for a key policy audit.


Output Format:

<key_id>  <created_date>  <expiry_date>  <age_in_days>  <expires_in_days>  <is_expired>  <service_account_email>


You can supply a service account credentials file to authenticate with or just use ADC via:

    gcloud auth application-default login


See Also - similar scripts in the DevOps Bash tools repo:

    https://github.com/HariSekhon/DevOps-Bash-tools/

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime
import json
import os
import sys
import traceback
from google.oauth2 import service_account
import googleapiclient.discovery
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, log_option, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


class GcpServiceAccountCredentialKeys(CLI):

    def __init__(self):
        # Python 2.x
        super(GcpServiceAccountCredentialKeys, self).__init__()
        # Python 3.x
        # super().__init__()
        self.credentials_file = None
        self.service = None
        self.project = None
        self.no_expiry = None
        self.expired = None
        self.expires_within_days = None

    def add_options(self):
        super(GcpServiceAccountCredentialKeys, self).add_options()
        self.add_opt('-f', '--credentials-file', metavar='<credentials.json>',
                     default=os.getenv('GOOGLE_CREDENTIALS', \
                             os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
                     help='Credentials file ($GOOGLE_CREDENTIALS, ' + \
                                            '$GOOGLE_APPLICATION_CREDENTIALS)')
        self.add_opt('-p', '--project-id', metavar='<project_id>',
                     help='Google Cloud Project ID ($GOOGLE_PROJECT_ID, or inferred from credentials file')
        self.add_opt('-n', '--no-expiry', action='store_true', help='List only non-expiring keys')
        self.add_opt('-e', '--expired', action='store_true', help='List only expired keys')
        self.add_opt('-d', '--expires-within-days', type=int, help='List only keys that will expire within N days')

    def process_options(self):
        super(GcpServiceAccountCredentialKeys, self).process_options()
        self.no_args()
        project_id = self.get_opt('project_id')
        credsfile = self.get_opt('credentials_file')
        self.no_expiry = self.get_opt('no_expiry')
        self.expired = self.get_opt('expired')
        self.expires_within_days = self.get_opt('expires_within_days')
        #if not credsfile:
        #    self.usage('no --credentials-file given and ' + \
        #               'GOOGLE_CREDENTIALS / GOOGLE_APPLICATION_CREDENTIALS environment variables not populated')
        if credsfile:
            if not os.path.exists(credsfile):
                self.usage('credentials file not found: {}'.format(credsfile))
            self.credentials_file = credsfile
            log_option('credentials file', self.credentials_file)
        if not project_id:
            if credsfile:
                json_data = json.loads(open(credsfile).read())
                project_id = json_data['project_id']
            else:
                self.usage('--project-id not specified and no credentials file given from which to infer')
        self.project = project_id
        log_option('project', self.project)
        if self.expires_within_days is not None:
            validate_int(self.expires_within_days, 'expires within days', 0)
            if self.no_expiry:
                self.usage('--expires-within-days and --no-expiry are mutually exclusive')
            if self.expired:
                self.usage('--expires-within-days and --expired are mutually exclusive')
        if self.no_expiry and self.expired:
            self.usage('--expired and --no-expiry are mutually exclusive')

    def run(self):
        # defaults to looking for $GOOGLE_APPLICATION_CREDENTIALS or using Application Default Credentials
        # from 'gcloud auth application-default login' => ~/.config/gcloud/application_default_credentials.json
        credentials = None
        if self.credentials_file:
            log.debug('loading credentials')
            credentials = service_account.Credentials.from_service_account_file(
                filename=self.credentials_file,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )

        # cache_discovery=False avoids:
        # ImportError: file_cache is unavailable when using oauth2client >= 4.0.0 or google-auth
        self.service = googleapiclient.discovery.build('iam', 'v1', credentials=credentials, cache_discovery=False)

        for service_account_email in self.get_service_accounts():
            self.list_keys(service_account_email)

    def get_service_accounts(self):
        """ Returns a list of service account email addresses """

        log.debug('getting service accounts')
        service_accounts = self.service.projects()\
                                       .serviceAccounts()\
                                       .list(name='projects/{}'.format(self.project))\
                                       .execute()
        for account in service_accounts['accounts']:
            yield account['email']

    def list_keys(self, service_account_email):
        log.debug("getting keys for service account '%s'", service_account_email)
        keys = self.service.projects()\
                           .serviceAccounts()\
                           .keys()\
                           .list(name='projects/-/serviceAccounts/' + service_account_email).execute()

        for key in keys['keys']:
            if key['keyType'] == 'SYSTEM_MANAGED':
                continue
            _id = key['name'].split('/')[-1]
            created_date = key['validAfterTime']
            expiry_date = key['validBeforeTime']
            created_datetime = datetime.strptime(created_date, "%Y-%m-%dT%H:%M:%SZ")
            expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%dT%H:%M:%SZ")
            age_timedelta = datetime.utcnow() - created_datetime
            age_days = int(age_timedelta.total_seconds() / 86400)
            expired = False
            if expiry_date == '9999-12-31T23:59:59Z':
                expires_in_days = 'NEVER'
            else:
                expires_in_timedelta = expiry_datetime - datetime.utcnow()
                expires_in_days = int(expires_in_timedelta.total_seconds() / 86400)
                if expires_in_days < 1:
                    expired = True
            if self.no_expiry and (expires_in_days != 'NEVER'):
                continue
            if self.expired and expired:
                continue
            if self.expires_within_days is not None and \
               (expires_in_days == 'NEVER' or expires_in_days > self.expires_within_days):
                continue
            print('{id}  {created}  {expires}  {age:4d}  {expires_in:5s}  {expired}  {service_account}'.format(
                id=_id,
                created=created_date,
                expires=expiry_date,
                age=age_days,
                expires_in=expires_in_days,
                expired=expired,
                service_account=service_account_email
                ))


if __name__ == '__main__':
    GcpServiceAccountCredentialKeys().main()

#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-10-14 15:29:38 +0100 (Wed, 14 Oct 2020)
#
#  https://github.com/HariSekhon/DevOps-Python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/HariSekhon
#

"""

GCP Cloud Function to export a given Cloud SQL database to GCS via PubSub notifications from Cloud Scheduler

Solution Documentation:

    https://cloud.google.com/solutions/scheduling-cloud-sql-database-exports-using-cloud-scheduler

GCP Cloud PubSub should be sent payloads like this by Cloud Scheduler (replacing the env vars with your literals):

{
    "project":  "${GOOGLE_PROJECT_ID}",
    "instance": "${SQL_INSTANCE_HOST}",
    "database": "${DATABASE}",
    "bucket":   "${BUCKET_NAME}"
}

Tested on GCP Cloud Functions with Python 3.7

"""

# https://cloud.google.com/functions/docs/writing/specifying-dependencies-python

# Code below is based on solution sample code from the link above

#import os
import base64
import logging
import json

from datetime import datetime
from httplib2 import Http

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials


# pylint: disable=unused-argument
def main(event, context):
#    if os.getenv("DEBUG"):
#        # debug level logs don't appear in function details logs tab even with
#        # DEBUG=1 runtime env var set and logs severity filter set to >= DEBUG
#        #logging.debug('event: %s', event)
#        #logging.debug('context: %s', context)
#        logging.info('event: %s', event)
#        logging.info('context: %s', context)
    data = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    credentials = GoogleCredentials.get_application_default()

    service = discovery.build('sqladmin', 'v1beta4', http=credentials.authorize(Http()), cache_discovery=False)

    project = data['project']
    bucket = data['bucket']
    bucket = bucket.lstrip('gs://')
    instance = data['instance']
    database = data['database']
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    # .gz extension so it is auto-compressed, saving storage space + billing
    backup_uri = "gs://{bucket}/backups/sql/{instance}--{database}--{timestamp}.sql.gz".format(
        bucket=bucket,
        instance=instance,
        database=database,
        timestamp=timestamp)

    instances_export_request_body = {
        "exportContext": {
            "kind": "sql#exportContext",
            "fileType": "SQL",
            "uri": backup_uri,
            "databases": [
                database
            ]
        }
    }

    try:
        logging.info("Requesting project '%s' database instance '%s' runs a backup export to bucket '%s' path '%s'",
                     project,
                     instance,
                     bucket,
                     backup_uri)
        request = service.instances().export(
            project=project,
            instance=instance,
            body=instances_export_request_body
        )
        response = request.execute()
    except HttpError as err:
        logging.error("Backup FAILED. Reason: %s", err)
    else:
        logging.info("Backup Task triggered: %s", response)

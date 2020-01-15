#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-01-14 17:45:38 +0000 (Tue, 14 Jan 2020)
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

Generate and print an S3 pre-signed URL

Can do the same with the following AWS CLI command:

aws s3 presign s3://<bucket>/<key> [--expires-in <secs>]

Will generate a pre-signed URL even when the bucket and object key don't exist!

(you will get a runtime error when requesting the link that the bucket or object doesn't exist)


Uses the Boto library, read here for the list of ways to configure your AWS credentials:

    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import sys
import boto3

__author__ = 'Hari Sekhon'
__version__ = '0.1.1'

def main():
    parser = argparse.ArgumentParser(
        description='Generate an AWS S3 pre-signed URL to access an S3 object without logging in')
    parser.add_argument('bucket', help='Bucket Name')
    parser.add_argument('key', help='Key')
    parser.add_argument('expiration', nargs='?', default=3600, help='Expiration of URL in seconds')
    args = parser.parse_args()

    # more useful if doing this programmatically as we can do this on the command line via AWS CLI
    conn = boto3.client('s3')
    url = conn.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': args.bucket,
            'Key': args.key
        },
        ExpiresIn=args.expiration
    )
    print(url)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Control-C...', file=sys.stderr)

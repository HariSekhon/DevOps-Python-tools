#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2021-05-24 16:03:30 +0100 (Mon, 24 May 2021)
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

GCP Cloud Function to query ifconfig.co to show our IP information for debugging VPC Connector access
routing via specified VPC Network to using default NAT Gateway

Example usage: check GCF source IP to compare if it's permitted through Cloudflare / Firewall rules

The HTTP request is irrelevant, just pass an empty JSON document '{}', although we could pass the website to query
in a field in which case this would just act as a proxy.

See Also: gcp_cloud_function_proxy/main.py


Tested on GCP Cloud Functions with Python 3.9

"""

# https://cloud.google.com/functions/docs/writing/http#writing_http_content-python

# https://cloud.google.com/functions/docs/writing/specifying-dependencies-python

import requests

def main(_):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    req = requests.get('http://ifconfig.co/json')  # show our IP information for debugging VPC connector routing
    status_code = req.status_code
    status_message = req.reason
    content = req.text
    return "{} {}\n\n{}".format(status_code, status_message, content)

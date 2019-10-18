#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-23 15:45:28 +0200 (Fri, 23 Sep 2016)
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

Tool to trigger Ambari service checks, can find and trigger all service checks with a simple --all switch

Written to get around a state in Ambari Express Upgrade complaining that the service checks hadn't run since the last
configuration changes (https://issues.apache.org/jira/browse/AMBARI-18470). This works nicely to force a re-run of all
service checks and clear the state error. In the event that one or more services will fail, you can also try the other
workaround of adding stack.upgrade.bypass.prechecks=true to ambari-server.properties and restarting ambari server
(I've used both of these solutions in different situations on a couple of different HDP cluster upgrades).

Tested on Ambari 2.2.0, 2.4.0 with Hortonworks HDP 2.3.2, 2.4.0, 2.5.0

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import logging
import json
import os
#import re
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
    from harisekhon.utils import log, die, support_msg_api, code_error, isInt, isList, jsonpp
    from harisekhon.utils import validate_host, validate_port, validate_user, validate_password, validate_chars
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2.2'


class AmbariTriggerServiceChecks(CLI):

    def __init__(self):
        # Python 2.x
        super(AmbariTriggerServiceChecks, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host = 'localhost'
        self.port = 8080
        self.user = 'admin'
        self.password = None
        self.cluster = None
        self.services = None
        self.protocol = 'http'
        self.url_base = None
        self.watch = False
        self.verbose_default = 2
        self.timeout_default = 7200

    def add_options(self):
        self.add_hostoption(name='Ambari', default_host=self.host, default_port=self.port)
        self.add_useroption(name='Ambari', default_user=self.user)
        self.add_opt('-C', '--cluster', help='Cluster to request service checks on ' +
                     '(if Ambari only manages one cluster will detect and not require this option)')
        self.add_opt('-a', '--all', action='store_true', help='Trigger all service checks')
        self.add_opt('-s', '--services', help='Trigger service checks for given list of services (comma separated)')
        self.add_opt('-w', '--wait', action='store_true',
                     help='Wait for checks to complete before returning, ' +
                     'prints status of the service check in progress once per second until completion')
        self.add_opt('--cancel', action='store_true', help='Cancel all pending service check operations')
        self.add_opt('-S', '--ssl', action='store_true', help='use SSL when connecting to Ambari')
        self.add_opt('-L', '--list-clusters', action='store_true',
                     help='List clusters managed by Ambari and exit')
        self.add_opt('-l', '--list-services', action='store_true',
                     help='List services managed by Ambari for given --cluster and exit')
        self.add_quietoption()

    def process_args(self):
        self.no_args()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        self.user = self.get_opt('user')
        self.password = self.get_opt('password')
        self.cluster = self.get_opt('cluster')
        self.watch = self.get_opt('wait')
        if self.get_opt('ssl'):
            self.protocol = 'https'
        # must evaluate this late to pick up https protocol, not in __init__
        self.url_base = '{protocol}://{host}:{port}/api/v1'.format(host=self.host,
                                                                   port=self.port,
                                                                   protocol=self.protocol)
    def run(self):
        validate_host(self.host)
        validate_port(self.port)
        validate_user(self.user)
        validate_password(self.password)
        all_services = self.get_opt('all')
        services_str = self.get_opt('services')
        cancel = self.get_opt('cancel')
        if cancel and (all_services or services_str):
            self.usage('cannot specify --cancel and --services/--all simultaneously' +
                       ', --cancel will cancel all pending service checks')
        if all_services and services_str:
            self.usage('cannot specify --all and --services simultaneously, they are mutually exclusive')
        services_requested = []
        if services_str:
            services_requested = [service.strip().upper() for service in services_str.split(',')]
        list_clusters = self.get_opt('list_clusters')
        list_services = self.get_opt('list_services')
        clusters = self.get_clusters()
        if list_clusters:
            if self.verbose > 0:
                print('Ambari Clusters:\n')
            print('\n'.join(clusters))
            sys.exit(3)
        if not self.cluster and len(clusters) == 1:
            self.cluster = clusters[0]
            log.info('no --cluster specified, but only one cluster managed by Ambari' +
                     ', inferring --cluster=\'%s\'', self.cluster)
        validate_chars(self.cluster, 'cluster', r'\w\s\.-')
        self.services = self.get_services()
        if list_services:
            if self.verbose > 0:
                print('Ambari Services:\n')
            print('\n'.join(self.services))
            sys.exit(3)
        if not services_requested and not all_services and not cancel:
            self.usage('no --services specified, nor was --all requested')
        services_to_check = []
        if all_services:
            services_to_check = self.services
        else:
            for service_requested in services_requested:
                if service_requested not in self.services:
                    die('service \'{0}\' is not in the list of available services in Ambari!'.format(service_requested)
                        + ' Here is the list of services available:\n' + '\n'.join(self.services))
            services_to_check = services_requested
        if cancel:
            self.cancel_service_checks()
        else:
            self.request_service_checks(services_to_check)

    # throws (URLError, BadStatusLine) - catch in caller for more specific exception handling error reporting
    def req(self, url_suffix, data=None, request_type='GET'):
        x_requested_by = self.user
        url = self.url_base + '/' + url_suffix.lstrip('/')
        if self.user == 'admin':
            x_requested_by = os.getenv('USER', self.user)
        headers = {'X-Requested-By': x_requested_by}
        log.debug('X-Requested-By: %s', x_requested_by)
        try:
            if request_type == 'PUT':
                log.debug('PUT %s', url)
                log.debug('PUTing data:\n\n%s' % data)
                result = requests.put(url, auth=(self.user, self.password), headers=headers, data=data)
            elif data:
                log.debug('POST %s', url)
                log.debug('POSTing data:\n\n%s' % data)
                result = requests.post(url, auth=(self.user, self.password), headers=headers, data=data)
            else:
                log.debug('GET %s', url)
                result = requests.get(url, auth=(self.user, self.password), headers=headers)
        except requests.exceptions.RequestException as _:
            die(_)
        if log.isEnabledFor(logging.DEBUG):
            log.debug('headers:\n%s' % '\n'.join(['%(key)s:%(value)s' % locals()
                                                  for (key, value) in result.headers.items()])) # pylint: disable=unused-variable
            log.debug('status code: %s' % result.status_code)
            log.debug('body:\n%s' % result.text)
        if result.status_code != 200:
            try:
                message = result.json()['message']
                if message and message != result.reason:
                    if log.isEnabledFor(logging.DEBUG):
                        raise requests.exceptions.RequestException('%s %s: %s' \
                              % (result.status_code, result.reason, message))
                    else:
                        die('{0} {1}: {2}'.format(result.status_code, result.reason, message))
            # raised by ['message'] field not existing
            except KeyError:
                pass
            # raised by .json() No JSON object could be decoded
            except ValueError:
                pass
        result.raise_for_status()
        return result.text

    def get(self, url_suffix):
        return self.req(url_suffix)

    def post(self, url_suffix, data):
        return self.req(url_suffix, data)

    def put(self, url_suffix, data):
        return self.req(url_suffix, data, request_type='PUT')

    def get_clusters(self):
        content = self.get('/clusters')
        clusters = set()
        try:
            _ = json.loads(content)
            for item in _['items']:
                cluster = item['Clusters']['cluster_name']
                clusters.add(cluster)
        except (KeyError, ValueError) as _:
            die('failed to parse cluster name: {0}'.format(_) + support_msg_api())
        return sorted(list(clusters))

    def get_services(self):
        content = self.get('/clusters/{cluster}/services'.format(cluster=self.cluster))
        services = set()
        try:
            _ = json.loads(content)
            for item in _['items']:
                service = item['ServiceInfo']['service_name']
                services.add(service)
        except (KeyError, ValueError) as _:
            die('failed to parse services: {0}'.format(_) + support_msg_api())
        return sorted(list(services))

    def get_request_ids(self):
        content = self.get('/clusters/{cluster}/requests'.format(cluster=self.cluster))
        try:
            _ = json.loads(content)
            request_ids = []
            for item in _['items']:
                if item['Requests']['cluster_name'] == self.cluster:
                    request_id = item['Requests']['id']
                    if not isInt(request_id):
                        die('request id returned was not an integer! ' + support_msg_api())
                    request_ids.append(request_id)
            return request_ids
        except (KeyError, ValueError) as _:
            die('failed to parse response for request IDs: {0}. '.format(_) + support_msg_api())

    def cancel_service_checks(self):
        log.info('cancelling all requests matching service check context')
        request_ids = self.get_request_ids()
        #re_context = re.compile(r'.+ Service Check \(batch \d+ of \d+\)', re.I)
        cancel_payload = '{"Requests":{"request_status":"ABORTED","abort_reason":"Aborted by user"}}'
        for request_id in request_ids:
            content = self.get('/clusters/{cluster}/requests/{request_id}'
                               .format(cluster=self.cluster, request_id=request_id))
            try:
                _ = json.loads(content)
                request_context = _['Requests']['request_context']
                if 'Service Check' in request_context:
                    log.info('cancelling request_id %s (%s)', request_id, request_context)
                    self.put('/clusters/{cluster}/requests/{request_id}'
                             .format(cluster=self.cluster, request_id=request_id), data=cancel_payload)
            except (KeyError, ValueError) as _:
                die('failed to parse response for request_id {0}. '.format(request_id) + support_msg_api())

    def request_service_checks(self, services):
        log.debug('requesting service checks for services: %s', services)
        if not isList(services):
            code_error('non-list passed to request_service_checks')
        url_suffix = '/clusters/{cluster}/request_schedules'.format(cluster=self.cluster)
        payload = self.gen_payload(services)
        log.info('sending batch schedule check request for services: ' + ', '.join(services))
        content = self.post(url_suffix=url_suffix, data=payload)
        try:
            _ = json.loads(content)
            request_schedule_id = _['resources'][0]['RequestSchedule']['id']
            log.info('RequestSchedule %s submitted', request_schedule_id)
            href = _['resources'][0]['href']
            if href != self.url_base.rstrip('/') + '/clusters/{0}/request_schedules/{1}'\
                                                   .format(self.cluster, request_schedule_id):
                raise ValueError('href does not match expected request_schedules URI!')
            if self.watch:
                self.watch_scheduled_request(request_schedule_id)
        except (KeyError, ValueError) as _:
            die('parsing schedule request response failed: ' + str(_) + '. ' + support_msg_api())

    def watch_scheduled_request(self, request_schedule_id):
        while True:
            content = self.get('/clusters/{0}/request_schedules/{1}'.format(self.cluster, request_schedule_id))
            status = self.parse_scheduled_request(content)
            if status == 'COMPLETED':
                return
            time.sleep(1)

    @staticmethod
    def parse_scheduled_request(content):
        try:
            _ = json.loads(content)
            if _['RequestSchedule']['status'] == 'COMPLETED':
                log.info('COMPLETED')
                return 'COMPLETED'
            for item in _['RequestSchedule']['batch']['batch_requests']:
                request_status = 'NO STATUS YET'
                if 'request_status' in item:
                    request_status = item['request_status']
                if request_status == 'COMPLETED':
                    continue
                request_body = item['request_body']
                request_body_dict = json.loads(request_body)
                command = request_body_dict['RequestInfo']['command']
                context = request_body_dict['RequestInfo']['context']
                log.info('{request_status}: {command}: {context}'.format(request_status=request_status,
                                                                         command=command,
                                                                         context=context))
                if request_status != 'ABORTED':
                    return 'IN_PROGRESS'
        except (KeyError, ValueError) as _:
            die('parsing schedule request status failed: ' + str(_) + '. ' + support_msg_api())

    def gen_payload(self, services=None):
        log.debug('generating payload for services: %s', services)
        if services is None or services == 'all':
            services = self.get_services()
        if not isList(services):
            code_error('non-list passed to gen_payload')
        # determined from here:
        # https://community.hortonworks.com/questions/11111/is-there-a-way-to-execute-ambari-service-checks-in.html
        payload = [
            {
                "RequestSchedule": {
                    "batch": [
                        {
                            "requests": []
                        },
                        {
                            "batch_settings": {
                                "batch_separation_in_seconds": 1,
                                "task_failure_tolerance": 1
                            }
                        }
                    ]
                }
            }
        ]
        service_count = len(services)
        for index in range(service_count):
            service = services[index]
            index += 1

            commandData = ""
            if service.upper() == "ZOOKEEPER" :
              # ZOOKEEPER service check command name is irregular ZOOKEEPER_QUORUM_SERVICE_CHECK, not ZOOKEEPER_SERVICE_CHECK
              commandData = "{service}_QUORUM_SERVICE_CHECK".format(service=service.upper())
            else :
              commandData = "{service}_SERVICE_CHECK".format(service=service.upper())

            payload[0]['RequestSchedule']['batch'][0]['requests'].append(
                {
                    "order_id": index,
                    "type": "POST",
                    "uri": "/api/v1/clusters/{0}/requests".format(self.cluster),
                    "RequestBodyInfo":{
                        "RequestInfo": {
                            "command": "{commandData}".format(commandData=commandData) ,
                            "context": "{service} Service Check (batch {index} of {total})".
                                       format(service=service, index=index, total=service_count)
                        },
                        "Requests/resource_filters":[
                            {
                                "service_name": service.upper()
                            }
                        ]
                    }
                }
            )
        payload_str = json.dumps(payload)
        if log.isEnabledFor(logging.DEBUG):
            log.debug('generated payload:\n%s', jsonpp(payload_str))
        return payload_str


if __name__ == '__main__':
    AmbariTriggerServiceChecks().main()

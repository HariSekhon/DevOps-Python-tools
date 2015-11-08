#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-08 14:09:50 +0000 (Sun, 08 Nov 2015)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

from __future__ import print_function

__author__ = 'Hari Sekhon'
__version__ = '0.1'

import base64
import json
import os
import sys
# using optparse rather than argparse for servers still on Python 2.6
from optparse import OptionParser
import urllib2
from urllib2 import URLError
sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])) + '/lib')
try:
    from HariSekhonUtils import *
    # import HariSekhon import CLI
except ImportError, e:
    print('module import failed: %s' % e)
    sys.exit(3)
except Exception, e:
    print('exception encountered during module import: %s' % e)
    sys.exit(3)

# TODO: POST /blueprints/$name - register blueprint with Ambari
# TODO: POST /clusters/$name - create cluster
# TODO: auto-store to git - see perl tools
# TODO: /cluster/$cluster?format=blueprint - retrieve specific cluster blueprint (setup cluster by hand and then export the blueprint)

class AmbariBlueprint():

    def __init__(self, host, port, user, password, ssl=False):
        # must set X-Requested-By in newer versions of Ambari
        self.X_Requested_By = os.getenv('USER', user)
        if not isHost(host) or not isPort(port) or not isUser(user) or not password:
            raise InvalidOptionException('invalid options passed to AmbariBlueprint()')
        proto    = 'http'
        if ssl:
            proto = 'https'
        self.host     = host
        self.port     = port
        self.user     = user
        self.url_base = '%(proto)s://%(host)s:%(port)s/api/v1' % locals()
        # hack per req because otherwise needs to catch and then retry which is tedious
        self.base64authtok = base64.encodestring('%s:%s' % (user, password)).replace('\n', '')
        ## doesn't work with first req
        # passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        # passman.add_password(None, '%(proto)s://%(host)s:%(port)s/' % locals(), user, password)
        # auth_handler = urllib2.HTTPBasicAuthHandler(passman)
        ## doesn't work with first req
        # auth_handler.add_password(
        ##                            realm='Ambari',
        #                           None,
        #                           '%(proto)s://%(host)s:%(port)s/' % locals(),
        #                           user,
        #                           password)
        # opener = urllib2.build_opener(auth_handler)
        # urllib2.install_opener(opener)
        self.blueprint_dir = os.path.join(os.path.dirname(sys.argv[0]), 'ambari_blueprint_data')
        try:
            if not os.path.exists(self.blueprint_dir):
                log.info("creating blueprint data dir '%s'" % self.blueprint_dir)
                os.mkdir(self.blueprint_dir)
            if not os.path.isdir(self.blueprint_dir):
                raise IOError("blueprint dir '%s'already taken and is not a directory" % self.blueprint_dir)
        except IOError, e:
            die("'failed to create dir '%s': %s" % (self.blueprint_dir, e))

    def list_blueprints(self):
        url = self.url_base + '/blueprints'
        log.info("contacting Ambari as '%s'" % self.user)
        log.info('GET %s' % url)
        req = urllib2.Request(url)
        req.add_header('X-Requested-By', self.X_Requested_By)
        req.add_header("Authorization", "Basic %s" % self.base64authtok)
        try:
            data = urllib2.urlopen(req, None, 30)
        except URLError, e:
            log.critical('failed to fetch Ambari Blueprints: %s' % e)
            quit('CRITICAL', 'failed to fetch list of Ambari Blueprints: %s' % e)
        jsonData = json.load(data)
        log.debug('jsonData = %s' % jsonData)
        try:
            #return [ item['href'] for item in jsonData['items'] ]
            return [ item['Blueprints']['blueprint_name'] for item in jsonData['items'] ]
        except Exception, e:
            quit('CRITICAL', 'Ambari returned no blueprints: %s' % e)

    def fetch_blueprint(self, blueprint):
        url = self.url_base + '/blueprints/%s' % blueprint
        log.info("contacting Ambari as '%s'" % self.user)
        log.info('GET %s' % url)
        req = urllib2.Request(url)
        req.add_header('X-Requested-By', self.X_Requested_By)
        req.add_header("Authorization", "Basic %s" % self.base64authtok)
        try:
            data = urllib2.urlopen(req, None, 30)
        except URLError, e:
            err = "failed to fetch Ambari Blueprint '%s': %s" % (blueprint, e)
            log.critical(err)
            quit('CRITICAL', err)
        jsonData = json.load(data)
        log.debug('blueprint = %s' % jsonData)
        return json.dumps(jsonData, sort_keys=True, indent=4, separators=(',', ': '))

    def save_blueprint(self, blueprint):
        data = self.fetch_blueprint(blueprint)
        if data == None:
            err = "blueprint '%s' returned None" % blueprint
            log.critical(err)
            quit('CRITICAL', err)
        blueprint_file = os.path.join(self.blueprint_dir, blueprint.lower() + '.json')
        try:
            log.info("writing blueprint '%s' to file '%s'" % (blueprint, blueprint_file))
            f = open(blueprint_file, 'w')
            f.write(data)
            f.close()
        except IOError, e:
            quit('CRITICAL', "failed to write blueprint file to '%s': %s" % (blueprint_file, e))

    def save_all(self):
        for blueprint in self.list_blueprints():
            self.save_blueprint(blueprint)


def main():
    parser = OptionParser()
    parser.add_option('-H', '--host', dest='host', help='Ambari Host ($AMBARI_HOST)', metavar='<host>')
    parser.add_option('-P', '--port', dest='port', help='Ambari Port ($AMBARI_PORT, default 8080)', metavar='8080')
    parser.add_option('-u', '--user', dest='user', help='Ambari login user ($AMBARI_USER)', metavar='<user>')
    parser.add_option('-p', '--password', dest='password', help='Ambari login password ($AMBARI_PASSWORD)', metavar='<password>')
    parser.add_option('-s', '--ssl', dest='ssl', help='Use SSL connection', action='store_true', default=False)
    parser.add_option('-b', '--blueprint', dest='blueprint', help='Ambari blueprint name', metavar='<name>')
    # parser.add_option('-v', '--verbose', dest='verbose', help='Verbose mode (use multiple times for increasing verbosity)', action='count')

    host     = os.getenv('AMBARI_HOST')
    port     = os.getenv('AMBARI_PORT', 8080)
    user     = os.getenv('AMBARI_USER')
    password = os.getenv('AMBARI_PASSWORD')
    ssl      = False

    (options, args) = parser.parse_args()

    host = options.host if options.host else host
    port = options.port if options.port else port
    user = options.user if options.user else user
    password = options.password if options.password else password
    ssl = options.ssl if options.ssl else ssl
    blueprint = options.blueprint if options.blueprint else None
    # verbose = options.verbose

    log.setLevel(logging.INFO)
    # log.setLevel(logging.WARN)
    # if verbose > 1:
    #     log.setLevel(logging.INFO)
    # if verbose > 2:
    #     log.setLevel(logging.DEBUG)

    try:
        validate_host(host)
        validate_port(port)
        validate_user(user)
        validate_password(password)
    except InvalidOptionException, e:
        usage(parser, e)

    if args:
        usage(parser)

    a = AmbariBlueprint(host, port, user, password, ssl)
    if options.blueprint:
        a.save_blueprint(blueprint)
    else:
        a.save_all()
    log.info('Completed')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
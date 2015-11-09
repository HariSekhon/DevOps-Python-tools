#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-08 14:09:50 +0000 (Sun, 08 Nov 2015)
#  (re-instantiated from a Perl version in 2014)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

"""

Tool to fetch and save Ambari Blueprints and/or Blueprint existing clusters

Tested on Ambari 2.1.0 for Hortonworks HDP 2.2 & 2.3 clusters

"""

from __future__ import print_function

__author__ = 'Hari Sekhon'
__version__ = '0.5'

import base64
import json
import logging
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

# TODO: POST /blueprints/$name - register POST blueprint.json with Ambari
# TODO: POST /clusters/$name - create cluster POST hostmapping.json
# TODO: auto-store to git - see perl tools

class AmbariBlueprint():

    def __init__(self, host, port, user, password, ssl=False, dir='', keep_config=False):
        # must set X-Requested-By in newer versions of Ambari
        # log.info("contacting Ambari as '%s'" % self.user)
        self.X_Requested_By = os.getenv('USER', user)
        if not isHost(host) or not isPort(port) or not isUser(user) or not password:
            raise InvalidOptionException('invalid options passed to AmbariBlueprint()')
        proto    = 'http'
        if ssl:
            proto = 'https'
        self.host     = host
        self.port     = port
        self.user     = user
        self.keep_config = keep_config
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
        if dir:
            self.blueprint_dir = dir
        else:
            self.blueprint_dir = os.path.join(os.path.dirname(sys.argv[0]), 'ambari_blueprints')
        try:
            if not os.path.exists(self.blueprint_dir):
                log.info("creating blueprint data dir '%s'" % self.blueprint_dir)
                os.mkdir(self.blueprint_dir)
            if not os.path.isdir(self.blueprint_dir):
                raise IOError("blueprint dir '%s'already taken and is not a directory" % self.blueprint_dir)
        except IOError, e:
            die("'failed to create dir '%s': %s" % (self.blueprint_dir, e))

    def list_clusters(self):
        jsonData = self.list('clusters')
        try:
            return [ item['Clusters']['cluster_name'] for item in jsonData['items'] ]
        except Exception, e:
            quit('CRITICAL', 'Ambari returned no clusters: %s' % e)

    def list_blueprints(self):
        jsonData = self.list('blueprints')
        try:
            return [ item['Blueprints']['blueprint_name'] for item in jsonData['items'] ]
        except Exception, e:
            quit('CRITICAL', 'Ambari returned no blueprints: %s' % e)

    def list(self, url):
        url = self.url_base + '/' + url
        log.debug('GET %s' % url)
        req = urllib2.Request(url)
        req.add_header('X-Requested-By', self.X_Requested_By)
        req.add_header("Authorization", "Basic %s" % self.base64authtok)
        try:
            data = urllib2.urlopen(req, None, 30)
        except URLError, e:
            err = 'failed to fetch list of Ambari Blueprints: %s' % e
            log.critical(err)
            quit('CRITICAL', err)
        jsonData = json.load(data)
        log.debug('jsonData = %s' % jsonData)
        return jsonData

    def fetch_cluster(self, cluster):
        return self.fetch('clusters/%s?format=blueprint' % cluster)

    def fetch_blueprint(self, blueprint):
        return self.fetch('blueprints/%s' % blueprint)

    def fetch(self, url):
        url = self.url_base + '/' + url
        log.debug('GET %s' % url)
        req = urllib2.Request(url)
        req.add_header('X-Requested-By', self.X_Requested_By)
        req.add_header("Authorization", "Basic %s" % self.base64authtok)
        try:
            data = urllib2.urlopen(req, None, 30)
        except URLError, e:
            err = "failed to fetch Ambari Blueprint from '%s': %s" % (url, e)
            log.critical(err)
            quit('CRITICAL', err)
        jsonData = json.load(data)
        if not self.keep_config:
            log.debug('not keeping config section of blueprint')
            del jsonData['configurations']
        log.debug('blueprint = %s' % jsonData)
        return json.dumps(jsonData, sort_keys=True, indent=4, separators=(',', ': '))

    def save_blueprint(self, blueprint):
        data = self.fetch_blueprint(blueprint)
        self.save(blueprint, data)

    def save_cluster(self, cluster):
        data = self.fetch_cluster(cluster)
        self.save(cluster, data)

    def save(self, name, data):
        if data == None:
            err = "blueprint '%s' returned None" % name
            log.critical(err)
            quit('CRITICAL', err)
        blueprint_file = os.path.join(self.blueprint_dir, name.lower() + '.json')
        try:
            log.info("writing blueprint '%s' to file '%s'" % (name, blueprint_file))
            f = open(blueprint_file, 'w')
            f.write(data)
            f.close()
        except IOError, e:
            quit('CRITICAL', "failed to write blueprint file to '%s': %s" % (blueprint_file, e))

    def save_all(self):
        blueprints = self.list_blueprints()
        clusters   = self.list_clusters()
        if not blueprints and not clusters:
            quit('UNKNOWN', 'no Ambari Blueprints or Clusters found on server')
        for blueprint in blueprints:
            self.save_blueprint(cluster)
        for cluster in clusters:
            self.save_cluster(cluster)


def main():
    parser = OptionParser()
    parser.add_option('-H', '--host', dest='host', help='Ambari Host ($AMBARI_HOST)', metavar='<host>')
    parser.add_option('-P', '--port', dest='port', help='Ambari Port ($AMBARI_PORT, default: 8080)', metavar='8080')
    parser.add_option('-u', '--user', dest='user', help='Ambari login user ($AMBARI_USER, default: admin)', metavar='<user>')
    parser.add_option('-p', '--password', dest='password', help='Ambari login password ($AMBARI_PASSWORD)', metavar='<password>')
    # TODO: certificate validation not tested yet
    parser.add_option('-s', '--ssl', dest='ssl', help='Use SSL connection', action='store_true', default=False)
    parser.add_option('-b', '--blueprint', dest='blueprint', help='Ambari blueprint name', metavar='<name>')
    parser.add_option('-c', '--cluster', dest='cluster', help='Ambari cluster to blueprint (case sensitive)', metavar='<name>')
    parser.add_option('-d', '--dir', dest='dir', help="Ambari Blueprints storage directory (defaults to 'ambari_blueprints' directory adjacent to this tool)", metavar='<dir>')
    parser.add_option('--keep-config', dest='keep_config', help='Keep cluster configuration section when querying a cluster', action='store_true', default=False)
    parser.add_option('-v', '--verbose', dest='verbose', help='Verbose mode', action='count', default=0)

    host     = os.getenv('AMBARI_HOST')
    port     = os.getenv('AMBARI_PORT', 8080)
    user     = os.getenv('AMBARI_USER', 'admin')
    password = os.getenv('AMBARI_PASSWORD')
    ssl      = False

    (options, args) = parser.parse_args()

    host = options.host if options.host else host
    port = options.port if options.port else port
    user = options.user if options.user else user
    password = options.password if options.password else password
    ssl = options.ssl if options.ssl else ssl
    blueprint = options.blueprint if options.blueprint else None
    cluster = options.cluster if options.cluster else None
    verbose = options.verbose

    # log.setLevel(logging.WARN)
    log.setLevel(logging.INFO)
    # log.info('verbose level: %s' % verbose)
    if verbose:
        log.setLevel(logging.DEBUG)

    try:
        validate_host(host)
        validate_port(port)
        validate_user(user)
        validate_password(password)
        if options.dir:
            validate_dirname(options.dir, 'blueprints')
    except InvalidOptionException, e:
        usage(parser, e)

    if args:
        usage(parser)

    if blueprint and cluster:
        usage(parser, '--blueprint/--cluster are mutually exclusive')

    a = AmbariBlueprint(host, port, user, password, ssl, options.dir, options.keep_config)
    if options.blueprint:
        a.save_blueprint(blueprint)
    elif options.cluster:
        a.save_cluster(cluster)
    else:
        a.save_all()
    log.info('Completed')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
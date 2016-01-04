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

Ambari Blueprints Tool

Features:

1. find and fetch all Ambari Blueprints and/or Blueprint existing clusters
2. fetch a specific given blueprint
3. blueprint an existing cluster (<== I like this one)
3. strips out href that is not valid to re-submit
4. strips out configuration settings values to make the blueprint more generic if specifying --strip-config
5. push a given blueprint file to Ambari, resetting a blueprint's name field on the fly to avoid field conflicts between adjacent blueprints
6. create a new cluster using a previously uploaded blueprint and a hostmapping file
7. list available blueprints, clusters and hosts

Ambari Blueprints are supported for Ambari 1.6.0 upwards.

Tested on Ambari 2.1.0 and 2.1.2.x and Hortonworks HDP 2.2 / 2.3 clusters

Example:
    # on source cluster
    ./ambari_blueprints.py --get --cluster myOriginalCluster --file myBlueprint.json --strip-config

    # on target cluster
    ./ambari_blueprints.py --push --blueprint myBlueprint --file myBlueprint.json
    ./ambari_blueprints.py --create-cluster --cluster myTestCluster --file hostmappings.json

See the adjacent ambari_blueprints directory for sample templates.

Ambari Blueprints documentation

https://cwiki.apache.org/confluence/display/AMBARI/Blueprints
https://cwiki.apache.org/confluence/display/AMBARI/Blueprint+Support+for+HA+Clusters:

For custom repos see:

https://cwiki.apache.org/confluence/display/AMBARI/Blueprints#Blueprints-Step4:SetupStackRepositories(Optional)

"""

from __future__ import print_function

__author__ = 'Hari Sekhon'
__version__ = '0.8.0'

import base64
import json
import logging
import os
import requests
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'pylib'))
try:
    pass
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError as e:
    print('module import failed: %s' % e)
    sys.exit(4)

# TODO: auto-store to git - see perl tools


class AmbariBlueprintTool(CLI):

    def setup(self, host, port, user, password, ssl=False, **kwargs):
        # must set X-Requested-By in newer versions of Ambari
        self.X_Requested_By = user
        if user == 'admin':
            self.X_Requested_By = os.getenv('USER', user)
        #log.info("contacting Ambari as '%s'" % self.user)
        if not isHost(host) or not isPort(port) or not isUser(user) or not password:
            raise InvalidOptionException('invalid options passed to AmbariBlueprint()')
        proto    = 'http'
        if ssl:
            proto = 'https'
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.strip_config = False
        # if kwargs.has_key('strip_config') and kwargs['strip_config']:
        if 'strip_config' in kwargs and kwargs['strip_config']:
            self.strip_config = True
        self.timeout_per_req = 30
        self.url_base = '%(proto)s://%(host)s:%(port)s/api/v1' % locals()
        self.blueprint_dir = os.path.join(os.path.dirname(sys.argv[0]), 'ambari_blueprints')
        if 'dir' in kwargs and kwargs['dir']:
            self.blueprint_dir = kwargs['dir']
        if not isDirname(self.blueprint_dir):
            quit('UNKNOWN', 'invalid dir arg passed to AmbariBlueprintTool')
        try:
            if not self.blueprint_dir or not os.path.exists(self.blueprint_dir):
                log.info("creating blueprint data dir '%s'" % self.blueprint_dir)
                os.mkdir(self.blueprint_dir)
            if not os.path.isdir(self.blueprint_dir):
                raise IOError("blueprint dir '%s'already taken and is not a directory" % self.blueprint_dir)
        except IOError as e:
            die("'failed to create dir '%s': %s" % (self.blueprint_dir, e))

    def parse_cluster_name(self, item):
        if isStr(item):
            item = json.loads(item)
        try:
            return item['Clusters']['cluster_name']
        except Exception as e:
            quit('CRITICAL', 'failed to parse Ambari cluster name: %s' % e)

    def get_clusters(self):
        log.debug('get_clusters()')
        jsonData = self.list('clusters')
        return [self.parse_cluster_name(item) for item in jsonData['items']]

    def parse_blueprint_name(self, item):
        if isStr(item):
            item = json.loads(item)
        try:
            return item['Blueprints']['blueprint_name']
        except Exception as e:
            quit('CRITICAL', 'failed to parse Ambari blueprint name: %s' % e)

    def get_blueprints(self):
        # log.debug('get_blueprints()')
        jsonData = self.list('blueprints')
        return [self.parse_blueprint_name(item) for item in jsonData['items']]

    def parse_host_name(self, item):
        if isStr(item):
            item = json.loads(item)
        try:
            return item['Hosts']['host_name']
        except Exception as e:
            quit('CRITICAL', 'failed to parse Ambari host name: %s' % e)

    def get_hosts(self):
        log.debug('get_hosts()')
        jsonData = self.list('hosts')
        return [ self.parse_host_name(item) for item in jsonData['items'] ]

    def list(self, url_suffix):
        self.url = self.url_base + '/' + url_suffix
        try:
            response = self.get(url_suffix)
        except requests.exceptions.HTTPError as e:
            err = 'failed to fetch list of Ambari Blueprints: %s' % e
            # log.critical(err)
            quit('CRITICAL', err)
        jsonData = json.loads(response)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("jsonData = " + jsonpp(jsonData))
        return jsonData

    def get_cluster_blueprint(self, cluster):
        return self.fetch('clusters/%s?format=blueprint' % cluster)

    def get_blueprint(self, blueprint):
        return self.fetch('blueprints/%s' % blueprint)

    # throws (URLError, BadStatusLine) - catch in caller for more specific exception handling error reporting
    def req(self, url_suffix, data=None):
        self.url = self.url_base + '/' + url_suffix
        if data:
            log.debug('POST %s' % self.url)
        else:
            log.debug('GET %s' % self.url)
        # req = urllib.request.Request(self.url) #, data, self.timeout)
        # req.add_header('X-Requested-By', self.X_Requested_By)
        # req.add_header("Authorization", "Basic %s" % self.base64authtok)
        # response = urllib.request.urlopen(req, data, self.timeout_per_req)
        r = None
        headers = { 'X-Requested-By': self.X_Requested_By }
        if data:
            r = requests.post(self.url, auth=(self.user, self.password), headers=headers, data=data)
        else:
            r = requests.get(self.url, auth=(self.user, self.password), headers=headers)
        r.raise_for_status()
        return r.text

    def get(self, url_suffix):
        return self.req(url_suffix)

    def post(self, url_suffix, data):
        return self.req(url_suffix, data)

    def fetch(self, url_suffix):
        err = ''
        try:
            response = self.get(url_suffix)
        except requests.exceptions.HTTPError as e:
            err = "failed to fetch Ambari Blueprint from '%s': %s" % (self.url, e)
            # log.critical(err)
            quit('CRITICAL', e)
        jsonData = json.loads(response)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("blueprint = " + jsonpp(jsonData))
        try:
            del jsonData['href']
            log.debug("stripped href as it's not valid if re-submitting the blueprint to Ambari")
        except KeyError as e:
            pass
        # Ambari 2.1.3 supports this according to https://cwiki.apache.org/confluence/display/AMBARI/Blueprints#Blueprints-ClusterCreationTemplateStructure
        # jsonData['config_recommendation_strategy'] = 'NEVER_APPLY' # default
        # jsonData['config_recommendation_strategy'] = 'ONLY_STACK_DEFAULTS_APPLY'
        # jsonData['config_recommendation_strategy'] = 'ALWAYS_APPLY'
        if self.strip_config:
            log.info('stripping out config sections of blueprints to make more generic')
            try:
                del jsonData['configurations']
                for hostgroup in jsonData['host_groups']:
                    del hostgroup['configurations']
            except KeyError as e:
                pass
        try:
            jsonData['host_groups'] = list_sort_dicts_by_value(jsonData['host_groups'], 'name')
            for hostgroup in jsonData['host_groups']:
                hostgroup['components'] = list_sort_dicts_by_value(hostgroup['components'], 'name')
        except KeyError as e:
            quit('CRITICAL', 'failed to sort blueprint: %s' % e)
        return jsonpp(jsonData)

    def send(self, url_suffix, data):
        # log.debug('send(%s, %s)' % url_suffix, data)
        self.url = self.url_base + '/' + url_suffix
        err = ''
        conflict_err = " (is there an existing blueprint with the same --blueprint name or a blueprint with the same Blueprints -> blueprint_name field? Try changing --blueprint and/or the blueprint_name field in the blueprint file you're trying to --push)"
        try:
            response = self.post(url_suffix, data)
        except requests.exceptions.HTTPError as e:
            err = "failed to POST Ambari Blueprint to '%s': %s" % (self.url, e)
            if 'Conflict' in str(e):
                err += conflict_err
            # log.critical(err)
            quit('CRITICAL', err)
        try:
            jsonData = json.loads(response)
        except ValueError as e:
            log.debug('no valid json returned by Ambari server: %s' % e)
        if log.isEnabledFor(logging.DEBUG) and 'jsonData' in locals():
            log.debug("response = " + jsonpp(jsonData))
        return True

    def send_blueprint_file(self, file, name=''):
        # log.debug('send_blueprint_file(%s, %s)' % (file, name))
        validate_file(file, 'blueprint', nolog=True)
        try:
            fh = open(str(file))
            file_data = fh.read()
        except IOError as e:
            err = "failed to read Ambari Blueprint from file '%s': %s" % (file, e)
            # log.critical(err)
            quit('CRITICAL', err)
        if not name:
            try:
                name = self.parse_blueprint_name(file_data)
                log.info("name not specified, determined blueprint name from file contents as '%s'" % name)
            except KeyError as e:
                pass
        if not name:
            name = os.path.splitext(os.path.basename(file))[0]
            log.info("name not specified and couldn't determine blueprint name from blueprint data, reverting to using filename without extension '%s'" % name)
        # this solves the issue of having duplicate Blueprint.blueprint_name keys
        try:
            jsonData = json.loads(file_data)
            jsonData['Blueprints']['blueprint_name'] = name
            data = json.dumps(jsonData)
            log.info("reset blueprint field name to '%s'" % name)
        except ValueError as e:
            quit('CRITICAL', "invalid json found in file '%s': %s" % (file, name))
        except KeyError as e:
            log.warn('failed to reset the Blueprint name: %s' % e)
        return self.send_blueprint(name, data)

    def create_cluster(self, cluster, file, blueprint=''):
        # log.debug('create_cluster(%s, %s)' % (file, name))
        validate_file(file, 'cluster hosts mapping', nolog=True)
        try:
            fh = open(str(file))
            file_data = fh.read()
        except IOError as e:
            err = "failed to read Ambari cluster host mapping from file '%s': %s" % (file, e)
            # log.critical(err)
            quit('CRITICAL', err)
        log.info("creating cluster '%s' using file '%s'" % (cluster, file))
        if not isJson(file_data):
            quit('CRITICAL', "invalid json found in file '%s'" % file)
        # don't have access to a blueprint name to enforce reset here
        # jsonData = json.loads(file_data)
        # try:
        #     jsonData['Blueprints']['blueprint_name'] = blueprint
        # except KeyError, e:
        #     quit('CRITICAL', 'failed to (re)set blueprint name in cluster/hostmapping data before creating cluster')
        if blueprint:
            try:
                log.info("setting blueprint in cluster creation to '%s'" % blueprint)
                jsonData = json.loads(file_data)
                jsonData['blueprint'] = blueprint
                file_data = json.dumps(jsonData)
            except KeyError as e:
                log.warn("failed to inject blueprint name '%s' in to cluster creation" % blueprint)
        response = self.send('clusters/%s' % cluster, file_data)
        log.info("Cluster creation submitted, see Ambari web UI to track progress")
        return response

    def send_blueprint(self, name, data):
        # log.debug('save_blueprint(%s, %s)' % (name, data))
        blueprints = self.get_blueprints()
        if name in blueprints:
            log.warn("blueprint with name '%s' already exists" % name)
        log.info("sending blueprint '%s'" % name)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("blueprint data = '%s'" % data)
        # not exposing this to user via switches - shouldn't be using this right now
        # return self.send('blueprints/%s?validate_topology=false' % name, data)
        # quit('UNKNOWN', 'cluster creation not supported yet')
        return self.send('blueprints/%s' % name, data)

    def save_blueprint(self, blueprint, path=''):
        # log.debug('save_blueprint(%s, %s' % (blueprint, name))
        if not path:
            path = os.path.normpath(os.path.join(self.blueprint_dir, blueprint))
        data = self.get_blueprint(blueprint)
        # logged in save()
        # log.info("saving blueprint '%s' to file '%s" % (blueprint, path))
        if log.isEnabledFor(logging.DEBUG):
            log.debug("blueprint '%s' content = '%s'" % (blueprint, data))
        self.save(blueprint, path, data)

    def save_cluster(self, cluster, path=''):
        # log.debug('save_cluster(%s, %s)' % (cluster, name))
        if not path:
            path = os.path.normpath(os.path.join(self.blueprint_dir, cluster))
        data = self.get_cluster_blueprint(cluster)
        # logged in save()
        # log.info("saving cluster '%s' blueprint to file '%s'" % (cluster, path))
        if log.isEnabledFor(logging.DEBUG):
            log.debug("cluster '%s' blueprint content = '%s'" % (cluster, data))
        self.save(cluster, path, data)

    def save(self, name, path, data):
        # log.debug('save(%s, %s)' % (name, data))
        if data == None:
            err = "blueprint '%s' returned None" % name
            log.critical(err)
            quit('CRITICAL', err)
        # blueprint_file = os.path.basename(name).lower().rstrip('.json') + '.json'
        # if not os.pathsep not in blueprint_file:
        #     blueprint_file = os.path.normpath(os.path.join(self.blueprint_dir, blueprint_file))
        if os.path.splitext(path)[1] != '.json':
            path += '.json'
        try:
            log.info("writing blueprint '%s' to file '%s'" % (name, path))
            f = open(path, 'w')
            f.write(data)
            f.close()
            print("Saved blueprint '%s' to file '%s'" % (name, path))
        except IOError as e:
            quit('CRITICAL', "failed to write blueprint file to '%s': %s" % (path, e))

    def save_all(self):
        log.info('finding all blueprints and clusters to blueprint')
        blueprints = self.get_blueprints()
        clusters   = self.get_clusters()
        if not blueprints and not clusters:
            quit('UNKNOWN', 'no Ambari Blueprints or Clusters found on server')
        for blueprint in blueprints:
            self.save_blueprint(blueprint)
        for cluster in clusters:
            self.save_cluster(cluster)

    def print_blueprints(self):
        blueprints = self.get_blueprints()
        print('\nBlueprints (%s found):\n' % len(blueprints))
        if blueprints:
            [print(x) for x in blueprints]
        else:
            print('<No Blueprints Found>')
        clusters = self.get_clusters()
        print('\nClusters available to blueprint (%s found):\n' % len(clusters))
        if clusters:
            [print(x) for x in clusters]
        else:
            print('<No Clusters Found>')
        print()
        print('%s total extractable blueprints' % str(len(blueprints) + len(clusters)))
        sys.exit(0)

    def print_clusters(self):
        clusters = self.get_clusters()
        print('\nClusters available to blueprint (%s found):\n' % len(clusters))
        if clusters:
            [print(x) for x in clusters]
        else:
            print('<No Clusters Found>')
        print()
        sys.exit(0)

    def print_hosts(self):
        hosts = self.get_hosts()
        print('\nHosts (%s found):\n' % len(hosts))
        if hosts:
            # seems to come out already sorted(hosts)
            [print(x) for x in hosts]
        else:
            print('<No Hosts Found>')
        sys.exit(0)

    def add_options(self):
        self.add_hostoption(name='Ambari', default_host='localhost', default_port=8080)
        self.add_useroption(name='Ambari', default_user='admin')
        # TODO: certificate validation not tested yet
        self.parser.add_option('-s', '--ssl', dest='ssl', help='Use SSL connection (not tested yet)', action='store_true', default=False)
        self.parser.add_option('-b', '--blueprint', dest='blueprint', help='Ambari blueprint name', metavar='<name>')
        self.parser.add_option('-c', '--cluster', dest='cluster', help='Ambari cluster to blueprint (case sensitive)', metavar='<name>')
        self.parser.add_option('--get', dest='get', help='Get and store Ambari Blueprints locally in --dir or --file', action='store_true')
        self.parser.add_option('--push', dest='push',  help='Push a local Ambari blueprint to the Ambari server', action='store_true')
        self.parser.add_option('--create-cluster', dest='create_cluster',  help='Create a cluster (requires --cluster and --file as well as previously uploaded Ambari Blueprint)', action='store_true')
        self.parser.add_option('-f', '--file', dest='file', help='Ambari Blueprint or Cluster creation file to --get write to or --push send from', metavar='<file.json>')
        self.parser.add_option('-d', '--dir', dest='dir', help="Ambari Blueprints storage directory if saving all blueprints (defaults to 'ambari_blueprints' directory adjacent to this tool)", metavar='<dir>')
        self.parser.add_option('--list-blueprints', dest='list_blueprints', help='List available blueprints', action='store_true', default=False)
        self.parser.add_option('--list-clusters', dest='list_clusters', help='List available clusters', action='store_true', default=False)
        self.parser.add_option('--list-hosts', dest='list_hosts', help='List available hosts', action='store_true', default=False)
        self.parser.add_option('--strip-config', dest='strip_config', help="Strip configuration sections out to make more generic. Use with caution, more advanced configurations like HDFS HA require some configuration settings in order to validate the topology when submitting a blueprint, so you'd have to add those config keys back in (suggest via a fully config'd cluster blueprint)", action='store_true', default=False)

    def process_args(self):
        options, args = self.options, self.args

        log.setLevel(logging.WARN)
        if options.verbose > 1:
            log.setLevel(logging.DEBUG)
        elif options.verbose:
            log.setLevel(logging.INFO)
        # log.info('verbose level: %s' % options.verbose)

        try:
            validate_host(options.host)
            validate_port(options.port)
            validate_user(options.user)
            validate_password(options.password)
            if options.dir:
                validate_dirname(options.dir, 'blueprints')
            if options.file:
                if options.push:
                    validate_file(options.file, 'blueprint')
                if options.create_cluster:
                    validate_file(options.file, 'cluster hosts mapping')
        except InvalidOptionException as e:
            self.usage(e)

        if self.args:
            self.usage('additional args detected')

        if options.get and options.blueprint and options.cluster:
            self.usage('--blueprint/--cluster are mutually exclusive when using --get')
        elif options.push and options.create_cluster:
            self.usage('--push and --create-cluster are mutually exclusive')
        elif options.create_cluster and not options.cluster:
            self.usage('--create-cluster requires specifying the name via --cluster')
        elif options.list_blueprints + options.list_clusters + options.list_hosts > 1:
            self.usage('can only use one --list switch at a time')
        elif options.file and (options.get and not (options.blueprint or options.cluster) ):
            self.usage("cannot specify --file without --blueprint/--cluster as it's only used when getting or pushing a single blueprint")
        elif options.file and (options.push and not (options.create_cluster or options.blueprint)):
            self.usage("cannot specify --file without --blueprint/--create-cluster as it's only used when getting or pushing a single blueprint or creating a cluster based on the blueprint")
        return options, args

    def run(self):
        options, args = self.process_args()
        self.setup(options.host,
                   options.port,
                   options.user,
                   options.password,
                   options.ssl,
                   dir=options.dir,
                   strip_config=options.strip_config)
        if options.list_blueprints:
            self.print_blueprints()
        elif options.list_clusters:
            self.print_clusters()
        elif options.list_hosts:
            self.print_hosts()
        elif options.get:
            if options.blueprint:
                self.save_blueprint(options.blueprint, options.file)
            elif options.cluster:
                self.save_cluster(options.cluster, options.file)
            else:
                self.save_all()
        elif options.push:
            if not options.file:
                self.usage('--file must be specified when pushing a blueprint to Ambari')
            self.send_blueprint_file(options.file, options.blueprint)
            print("Blueprint file '%s' sent and registered with Ambari as '%s'" % (options.file, options.blueprint))
        elif options.create_cluster:
            if not options.file:
                self.usage('--file must be specified with a hostsmapping.json file when creating a new Ambari cluster')
            self.create_cluster(options.cluster, options.file, options.blueprint)
            print("Ambari cluster '%s' creation job submitted, see '%s:%s' web UI for progress"
                                                                        % (options.cluster, options.host, options.port))
        else:
            self.usage('no options specified, try --get --cluster myCluster')
        log.info('Completed')

if __name__ == '__main__':
    AmbariBlueprintTool().main()
#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-08 14:09:50 +0000 (Sun, 08 Nov 2015)
#  (re-instantiated from a Perl version in 2014)
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

Ambari Blueprints Tool

Features:

1. find and fetch all Ambari Blueprints and/or Blueprint existing clusters
2. fetch a specific given blueprint
3. blueprint an existing cluster (<== use this one!)
4. strips out href that is not valid to re-submit
5. use --strip-config to strip out configuration settings values to make the blueprint more generic
6. push a given blueprint file to Ambari, resetting a blueprint's name field on the fly
   to avoid field conflicts between adjacent blueprints
7. create a new cluster using a previously uploaded blueprint and a hostmapping file
8. list available blueprints, clusters and hosts

Ambari Blueprints are supported for Ambari 1.6.0 upwards.

Tested on Ambari 2.1.0 and 2.1.2.x and Hortonworks HDP 2.2 / 2.3 clusters

Example:
    # on source cluster
    ./ambari_blueprints.py --get --cluster myOriginalCluster --file myBlueprint.json --strip-config

    # on target cluster
    ./ambari_blueprints.py --push --blueprint myBlueprint --file myBlueprint.json
    ./ambari_blueprints.py --create-cluster --cluster myTestCluster --blueprint myBlueprint --file hostmappings.json

Specifying --blueprint is optional for --create-cluster if blueprint is specified in the hostmappings file. If given
--blueprint it overrides field in the hostmappings for convenience than having to re-edit host templates

See the adjacent ambari_blueprints/ directory for sample templates.

See also the validate_json.py program in this same DevOps Python Tools repo for validating Ambari blueprint templates
to make hand editing them safer.

Ambari Blueprints documentation

https://cwiki.apache.org/confluence/display/AMBARI/Blueprints
https://cwiki.apache.org/confluence/display/AMBARI/Blueprint+Support+for+HA+Clusters:

For custom repos see:

https://cwiki.apache.org/confluence/display/AMBARI/Blueprints#Blueprints-Step4:SetupStackRepositories(Optional)

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# import base64
import json
import logging
import os
import sys
import requests
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    # import harisekhon.utils
    from harisekhon.utils import log, InvalidOptionException, qquit, die
    from harisekhon.utils import validate_file, validate_dirname, validate_host, validate_port, validate_user, \
        validate_password
    from harisekhon.utils import isStr, isHost, isPort, isUser, isDirname, isJson, jsonpp, list_sort_dicts_by_value
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.10.3'

class AmbariBlueprintTool(CLI):

    def __init__(self):
        super(AmbariBlueprintTool, self).__init__()
        self.blueprint_dir = os.path.join(os.path.dirname(sys.argv[0]), 'ambari_blueprints')
        self.host = None
        self.port = None
        self.user = os.getenv('USER', None)
        self.password = None
        self.strip_config = False
        self.timeout_default = 30
        self.timeout_per_req = 30
        self.url = None
        self.url_base = None
        self.x_requested_by = self.user

    def connection(self, host, port, user, password, ssl=False, **kwargs):
        # must set X-Requested-By in newer versions of Ambari
        self.x_requested_by = user
        if user == 'admin':
            self.x_requested_by = os.getenv('USER', user)
        #log.info("contacting Ambari as '%s'" % self.user)
        if not isHost(host) or not isPort(port) or not isUser(user) or not password:
            raise InvalidOptionException('invalid options passed to AmbariBlueprint()')
        proto = 'http'  # pylint: disable=unused-variable,possibly-unused-variable
        if ssl:
            proto = 'https'
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        # if kwargs.has_key('strip_config') and kwargs['strip_config']:
        if 'strip_config' in kwargs and kwargs['strip_config']:
            self.strip_config = True
        self.url_base = '%(proto)s://%(host)s:%(port)s/api/v1' % locals()
        if 'dir' in kwargs and kwargs['dir']:
            self.blueprint_dir = kwargs['dir']
        if not isDirname(self.blueprint_dir):
            qquit('UNKNOWN', 'invalid dir arg passed to AmbariBlueprintTool')
        try:
            if not self.blueprint_dir or not os.path.exists(self.blueprint_dir):
                log.info("creating blueprint data dir '%s'" % self.blueprint_dir)
                os.mkdir(self.blueprint_dir)
            if not os.path.isdir(self.blueprint_dir):
                raise IOError("blueprint dir '%s'already taken and is not a directory" % self.blueprint_dir)
        except IOError as _:
            die("'failed to create dir '%s': %s" % (self.blueprint_dir, _))

    @staticmethod
    def parse_cluster_name(item):
        if isStr(item):
            item = json.loads(item)
        try:
            return item['Clusters']['cluster_name']
        except KeyError as _:
            qquit('CRITICAL', 'failed to parse Ambari cluster name: %s' % _)

    def get_clusters(self):
        log.debug('get_clusters()')
        json_data = self.list('clusters')
        return [self.parse_cluster_name(item) for item in json_data['items']]

    @staticmethod
    def parse_blueprint_name(item):
        if isStr(item):
            item = json.loads(item)
        try:
            return item['Blueprints']['blueprint_name']
        except KeyError as _:
            qquit('CRITICAL', 'failed to parse Ambari blueprint name: %s' % _)

    def get_blueprints(self):
        # log.debug('get_blueprints()')
        json_data = self.list('blueprints')
        return [self.parse_blueprint_name(item) for item in json_data['items']]

    @staticmethod
    def parse_host_name(item):
        if isStr(item):
            item = json.loads(item)
        try:
            return item['Hosts']['host_name']
        except KeyError as _:
            qquit('CRITICAL', 'failed to parse Ambari host name: %s' % _)

    def get_hosts(self):
        log.debug('get_hosts()')
        json_data = self.list('hosts')
        return [self.parse_host_name(item) for item in json_data['items']]

    def list(self, url_suffix):
        self.url = self.url_base + '/' + url_suffix
        try:
            response = self.get(url_suffix)
        except requests.exceptions.RequestException as _:
            err = 'failed to fetch list of Ambari Blueprints: %s' % _
            # log.critical(err)
            qquit('CRITICAL', err)
        json_data = json.loads(response)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("json_data = " + jsonpp(json_data))
        return json_data

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
        # req.add_header('X-Requested-By', self.x_requested_by)
        # req.add_header("Authorization", "Basic %s" % self.base64authtok)
        # response = urllib.request.urlopen(req, data, self.timeout_per_req)
        result = None
        headers = {'X-Requested-By': self.x_requested_by}
        if data:
            log.debug('POSTing data:\n\n%s' % data)
            result = requests.post(self.url, auth=(self.user, self.password), headers=headers, data=data)
        else:
            result = requests.get(self.url, auth=(self.user, self.password), headers=headers)
        if log.isEnabledFor(logging.DEBUG):
            log.debug('headers:\n%s' % '\n'.join(['%(key)s:%(value)s' % locals()
                                                  for (key, value) in result.headers.items()])) # pylint: disable=unused-variable
            log.debug('status code: %s' % result.status_code)
            log.debug('body:\n%s' % result.text)
        if result.status_code != 200:
            try:
                message = result.json()['message']
                if message and message != result.reason:
                    raise requests.exceptions.RequestException('%s %s: %s' \
                          % (result.status_code, result.reason, message))
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

    def fetch(self, url_suffix):
        err = ''
        try:
            response = self.get(url_suffix)
        except requests.exceptions.RequestException as _:
            err = "failed to fetch Ambari Blueprint from '%s': %s" % (self.url, _)
            # log.critical(err)
            qquit('CRITICAL', err)
        json_data = json.loads(response)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("blueprint = " + jsonpp(json_data))
        try:
            del json_data['href']
            log.debug("stripped href as it's not valid if re-submitting the blueprint to Ambari")
        except KeyError as _:
            pass
        # Ambari 2.1.3 supports this according to:
        # https://cwiki.apache.org/confluence/display/AMBARI/Blueprints#Blueprints-ClusterCreationTemplateStructure
        # json_data['config_recommendation_strategy'] = 'NEVER_APPLY' # default
        # json_data['config_recommendation_strategy'] = 'ONLY_STACK_DEFAULTS_APPLY'
        # json_data['config_recommendation_strategy'] = 'ALWAYS_APPLY'
        if self.strip_config:
            log.info('stripping out config sections of blueprints to make more generic')
            try:
                del json_data['configurations']
                for hostgroup in json_data['host_groups']:
                    del hostgroup['configurations']
            except KeyError as _:
                pass
        try:
            json_data['host_groups'] = list_sort_dicts_by_value(json_data['host_groups'], 'name')
            for hostgroup in json_data['host_groups']:
                hostgroup['components'] = list_sort_dicts_by_value(hostgroup['components'], 'name')
        except KeyError as _:
            qquit('CRITICAL', 'failed to sort blueprint: %s' % _)
        return jsonpp(json_data)

    def send(self, url_suffix, data):
        # log.debug('send(%s, %s)' % url_suffix, data)
        self.url = self.url_base + '/' + url_suffix
        err = ''
        conflict_err = " (is there an existing blueprint with the same --blueprint name or a blueprint with the same Blueprints -> blueprint_name field? Try changing --blueprint and/or the blueprint_name field in the blueprint file you're trying to --push)" # pylint: disable=line-too-long
        try:
            response = self.post(url_suffix, data)
        except requests.exceptions.RequestException as _:
            err = "failed to POST Ambari Blueprint to '%s': %s" % (self.url, _)
            if 'Conflict' in str(_):
                err += conflict_err
            # log.critical(err)
            qquit('CRITICAL', err)
        try:
            json_data = json.loads(response)
        except ValueError as _:
            log.debug('no valid json returned by Ambari server: %s' % _)
        if log.isEnabledFor(logging.DEBUG) and 'json_data' in locals():
            log.debug("response = " + jsonpp(json_data))
        return True

    def send_blueprint_file(self, filename, name=''):
        # log.debug('send_blueprint_file(%s, %s)' % (filename, name))
        validate_file(filename, 'blueprint', nolog=True)
        try:
            _ = open(str(filename))
            file_data = _.read()
        except IOError as _:
            err = "failed to read Ambari Blueprint from file '%s': %s" % (filename, _)
            # log.critical(err)
            qquit('CRITICAL', err)
        if not name:
            try:
                name = self.parse_blueprint_name(file_data)
                log.info("name not specified, determined blueprint name from file contents as '%s'" % name)
            except KeyError as _:
                pass
        if not name:
            name = os.path.splitext(os.path.basename(filename))[0]
            log.info("name not specified and couldn't determine blueprint name from blueprint data, reverting to using filename without extension '%s'" % name) # pylint: disable=line-too-long
        # this solves the issue of having duplicate Blueprint.blueprint_name keys
        try:
            json_data = json.loads(file_data)
            json_data['Blueprints']['blueprint_name'] = name
            data = json.dumps(json_data)
            log.info("reset blueprint field name to '%s'" % name)
        except ValueError as _:
            qquit('CRITICAL', "invalid json found in file '%s': %s" % (filename, name))
        except KeyError as _:
            log.warn('failed to reset the Blueprint name: %s' % _)
        return self.send_blueprint(name, data)

    def create_cluster(self, cluster, filename, blueprint=''):
        # log.debug('create_cluster(%s, %s)' % (filename, name))
        validate_file(filename, 'cluster hosts mapping', nolog=True)
        try:
            _ = open(str(filename))
            file_data = _.read()
        except IOError as _:
            err = "failed to read Ambari cluster host mapping from file '%s': %s" % (filename, _)
            # log.critical(err)
            qquit('CRITICAL', err)
        log.info("creating cluster '%s' using file '%s'" % (cluster, filename))
        if not isJson(file_data):
            qquit('CRITICAL', "invalid json found in file '%s'" % filename)
        # don't have access to a blueprint name to enforce reset here
        # json_data = json.loads(file_data)
        # try:
        #     json_data['Blueprints']['blueprint_name'] = blueprint
        # except KeyError, e:
        #     qquit('CRITICAL', 'failed to (re)set blueprint name in cluster/hostmapping data before creating cluster')
        if blueprint:
            try:
                log.info("setting blueprint in cluster creation to '%s'" % blueprint)
                json_data = json.loads(file_data)
                json_data['blueprint'] = blueprint
                file_data = json.dumps(json_data)
            except KeyError as _:
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

    @staticmethod
    def save(name, path, data):
        # log.debug('save(%s, %s)' % (name, data))
        if data is None:
            err = "blueprint '%s' returned None" % name
            log.critical(err)
            qquit('CRITICAL', err)
        # blueprint_file = os.path.basename(name).lower().rstrip('.json') + '.json'
        # if not os.pathsep not in blueprint_file:
        #     blueprint_file = os.path.normpath(os.path.join(self.blueprint_dir, blueprint_file))
        if os.path.splitext(path)[1] != '.json':
            path += '.json'
        try:
            log.info("writing blueprint '%s' to file '%s'" % (name, path))
            _ = open(path, 'w')
            _.write(data)
            _.close()
            print("Saved blueprint '%s' to file '%s'" % (name, path))
        except IOError as _:
            qquit('CRITICAL', "failed to write blueprint file to '%s': %s" % (path, _))

    def save_all(self):
        log.info('finding all blueprints and clusters to blueprint')
        blueprints = self.get_blueprints()
        clusters = self.get_clusters()
        if not blueprints and not clusters:
            qquit('UNKNOWN', 'no Ambari Blueprints or Clusters found on server')
        for blueprint in blueprints:
            self.save_blueprint(blueprint)
        for cluster in clusters:
            self.save_cluster(cluster)

    def print_blueprints(self):
        blueprints = self.get_blueprints()
        print('\nBlueprints (%s found):\n' % len(blueprints))
        if blueprints:
            for _ in blueprints:
                print(_)
        else:
            print('<No Blueprints Found>')
        clusters = self.get_clusters()
        print('\nClusters available to blueprint (%s found):\n' % len(clusters))
        if clusters:
            for _ in clusters:
                print(_)
        else:
            print('<No Clusters Found>')
        print()
        print('%s total extractable blueprints' % str(len(blueprints) + len(clusters)))
        sys.exit(0)

    def print_clusters(self):
        clusters = self.get_clusters()
        print('\nClusters available to blueprint (%s found):\n' % len(clusters))
        if clusters:
            for _ in clusters:
                print(_)
        else:
            print('<No Clusters Found>')
        print()
        sys.exit(0)

    def print_hosts(self):
        hosts = self.get_hosts()
        print('\nHosts (%s found):\n' % len(hosts))
        if hosts:
            # seems to come out already sorted(hosts)
            for _ in hosts:
                print(_)
        else:
            print('<No Hosts Found>')
        sys.exit(0)

    def add_options(self):
        self.add_hostoption(name='Ambari', default_host='localhost', default_port=8080)
        self.add_useroption(name='Ambari', default_user='admin')
        # TODO: certificate validation not tested yet
        self.add_opt('-s', '--ssl', dest='ssl', action='store_true', default=False,
                     help='Use SSL connection (not tested yet)')
        self.add_opt('-b', '--blueprint', dest='blueprint',
                     help='Ambari blueprint name', metavar='<name>')
        self.add_opt('-c', '--cluster', dest='cluster', metavar='<name>',
                     help='Ambari cluster to blueprint (case sensitive)')
        self.add_opt('--get', dest='get', action='store_true',
                     help='Get and store Ambari Blueprints locally in --dir or --file')
        self.add_opt('--push', dest='push', action='store_true',
                     help='Push a local Ambari blueprint to the Ambari server')
        self.add_opt('--create-cluster', dest='create_cluster', action='store_true',
                     help='Create a cluster (requires --cluster and --file as well as previously uploaded Ambari Blueprint)') # pylint: disable=line-too-long
        self.add_opt('-f', '--file', dest='file', metavar='<file.json>',
                     help='Ambari Blueprint or Cluster creation file to --get write to or --push send from')
        self.add_opt('-d', '--dir', dest='dir', metavar='<dir>',
                     help="Ambari Blueprints storage directory if saving all blueprints (defaults to 'ambari_blueprints' directory adjacent to this tool)") # pylint: disable=line-too-long
        self.add_opt('--list-blueprints', dest='list_blueprints', action='store_true', default=False,
                     help='List available blueprints')
        self.add_opt('--list-clusters', dest='list_clusters', action='store_true', default=False,
                     help='List available clusters')
        self.add_opt('--list-hosts', dest='list_hosts', action='store_true', default=False,
                     help='List available hosts')
        self.add_opt('--strip-config', dest='strip_config', action='store_true', default=False,
                     help="Strip configuration sections out to make more generic. Use with caution more advanced configurations like HDFS HA require some configuration settings in order to validate the topology when submitting a blueprint, so you'd have to add those config keys back in (suggest via a fully config'd cluster blueprint)") # pylint: disable=line-too-long

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
        except InvalidOptionException as _:
            self.usage(_)

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
        elif options.file and (options.get and not (options.blueprint or options.cluster)):
            self.usage("cannot specify --file without --blueprint/--cluster as it's only used " + \
                       "when getting or pushing a single blueprint")
        elif options.file and (options.push and not (options.create_cluster or options.blueprint)):
            self.usage("cannot specify --file without --blueprint/--create-cluster as it's only used " + \
                       "when getting or pushing a single blueprint or creating a cluster based on the blueprint")
        return options, args

    def run(self):
        options = self.options
        self.connection(options.host,
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

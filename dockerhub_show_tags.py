#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-10 11:26:49 +0100 (Tue, 10 May 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help improve this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to show Docker tags for one or more DockerHub repos

Written for convenience as Docker CLI doesn't currently support this:

See https://github.com/docker/docker/issues/17238

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import json
import logging
import os
import re
import sys
import traceback
import urllib
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
    from harisekhon.utils import log, die, prog, isJson, jsonpp, support_msg_api, UnknownError
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.3'


class DockerHubTags(CLI):

    def __init__(self):
        # Python 2.x
        super(DockerHubTags, self).__init__()
        # Python 3.x
        # super().__init__()
        self._CLI__parser.usage = '{0} [options] repo1 repo2 ...'.format(prog)
        self.quiet = False
        self.timeout_default = 60
        self.url_base = 'https://registry.hub.docker.com/v2/repositories'
        self.url = self.url_base
        self.user = None
        self.password = None

    def add_options(self):
        self.add_opt('-q', '--quiet', action='store_true', default=False,
                     help='Output only the tags, one per line (useful for shell scripting)')

    def run(self):
        if not self.args:
            self.usage('no repos given as args')
        self.quiet = self.get_opt('quiet')
        if not self.quiet:
            # cheaper but lgtm hassling me, not a security issue but will shut them up
            print('\nDocker', end='')
            #if 'registry.hub.docker.com' in self.url_base:
            # match anchors but I prefer explicit anchor, more intuitive for other generic language coders
            if re.match(r'^https://registry\.hub\.docker\.com/', self.url_base):
                print('Hub')
            else:
                print(' Registry:  {0}'.format(self.url_base.split('/v2', 1)[0]))
            print()
        for arg in self.args:
            self.print_tags(arg)

    def print_tags(self, repo):
        # strip any accidental tag suffixes for convenience
        repo = repo.split(':')[0]
        if not self.quiet:
            print('repo: {0}'.format(repo))
            print('tags: ', end='')
        sys.stdout.flush()
        indent = '      '
        if self.quiet:
            indent = ''
        print('\n{0}'.format(indent).join(self.get_tags(repo)))
        if not self.quiet:
            print()

    def get_tags(self, repo):
        namespace = 'library'
        if ':' in repo:
            raise UnknownError('colon detected in repo \'{0}\', did you forget tag suffix in it'.format(repo))
        if '/' in repo:
            (namespace, repo) = repo.split('/', 1)
        # there is another endpoint but it requires authentication
        url = '{url_base}/{namespace}/{repo}/tags'\
              .format(url_base=self.url_base,
                      namespace=urllib.quote_plus(namespace),
                      repo=urllib.quote_plus(repo))
        # Docker Registry needs /list on end but DockerHub doesn't support this
        if 'dockerhub' not in prog:
            url += '/list'
        tag_list = []
        while True:
            (tags, url) = self.query(url)
            tag_list += tags
            if not url:
                break
        tag_list.sort()
        #tag_list.reverse()
        # put latest to the top of the list
        try:
            tag_list.insert(0, tag_list.pop(tag_list.index('latest')))
        except ValueError:
            pass
        return tag_list

    def query(self, url):
        log.debug('GET %s' % url)
        try:
            verify = True
            # workaround for Travis CI and older pythons - we're not exchanging secret data so this is ok
            #if os.getenv('TRAVIS'):
            #    verify = False
            if os.getenv('SSL_NOVERIFY') == '1':
                log.warn('disabling SSL verification')
                verify = False
            auth = None
            if self.user and self.password:
                auth = (self.user, self.password)
                log.debug('setting basic HTTP authenication using username: %s, password: <omitted>', self.user)
            req = requests.get(url, auth=auth, verify=verify)
        except requests.exceptions.RequestException as _:
            die(_)
        log.debug("response: %s %s", req.status_code, req.reason)
        log.debug("content:\n%s\n%s\n%s", '='*80, req.content.strip(), '='*80)
        if req.status_code != 200:
            die("%s %s" % (req.status_code, req.reason))
        if not isJson(req.content):
            die('invalid non-JSON response from Docker Registry!')
        if log.isEnabledFor(logging.DEBUG):
            print(jsonpp(req.content))
            print('='*80)
        tag_list = []
        try:
            json_data = json.loads(req.content)
            # DockerHub returns like this
            if 'results' in json_data:
                tag_list = [result['name'] for result in json_data['results']]
            # Docker Registry returns like this
            elif 'tags' in json_data:
                tag_list = json_data['tags']
            else:
                raise UnknownError('failed to parse response, found neither results nor tags fields. {0}'\
                                   .format(support_msg_api()))
            # could perhaps stack overflow in some scenario
            # not as functional programming 'cool' but will do own tail recursion and just while loop instead
            next_page_url = None
            if 'next' in json_data and json_data['next']:
            #    tag_list += self.query(json_data['next'])
                next_page_url = json_data['next']
            return (tag_list, next_page_url)
        except KeyError as _:
            die('failed to parse output from Docker Registry (format may have changed?): {0}'.format(_))


if __name__ == '__main__':
    DockerHubTags().main()

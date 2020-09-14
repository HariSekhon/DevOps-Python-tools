#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#  args: harisekhon
#
#  Author: Hari Sekhon
#  Date: 2016-05-27 13:15:30 +0100 (Fri, 27 May 2016)
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

Tool to search DockerHub repos and return a configurable number of results

Mimics 'docker search' results format but more flexible

Older Docker CLI didn't support configuring the returned number of search results and always returned 25:

https://github.com/docker/docker/issues/23055

Verbose mode will also show a summary for number of results displayed and total number of results available

Caveat: maxes out at 100 results, to iterate for more than that see dockerhub_search.sh

See also:

    dockerhub_search.sh

in the DevOps Bash tools repo - https://github.com/harisekhon/devops-python-tools

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import json
import logging
import os
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
    from harisekhon.utils import log, die, prog, isJson, jsonpp, isInt, validate_int, support_msg_api
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.2'


class DockerHubSearch(CLI):

    def __init__(self):
        # Python 2.x
        super(DockerHubSearch, self).__init__()
        # Python 3.x
        # super().__init__()
        self._CLI__parser.usage = '{0} [options] TERM'.format(prog)
        self.timeout_default = 30
        self.quiet = False

    def add_options(self):
        self.add_opt('-l', '--limit', default=50, type=int,
                     help='Number of results to return (default: 50)')
        self.add_opt('-q', '--quiet', action='store_true',
                     help='Output only the image names, one per line (useful for shell scripting)')

    def run(self):
        if not self.args:
            self.usage('no search term given as args')
        if len(self.args) > 1:
            self.usage('only single search term argument may be given')
        self.quiet = self.get_opt('quiet')
        term = self.args[0]
        log.info('term: %s', term)
        limit = self.get_opt('limit')
        validate_int(limit, 'limit', 1, 1000)
        self.print_results(self.args[0], limit)

    def print_results(self, term, limit=None):
        data = self.search(term, limit)
        results = {}
        longest_name = 8
        try:
            # collect in dict to order by stars like normal docker search command
            for item in data['results']:
                star = item['star_count']
                name = item['name']
                if len(name) > longest_name:
                    longest_name = len(name)
                if not isInt(star):
                    die("star count '{0}' for repo '{1}' is not an integer! {2}".format(star, name, support_msg_api()))
                results[star] = results.get(star, {})
                results[star][name] = results[star].get(name, {})
                result = {}
                result['description'] = item['description']
                result['official'] = '[OK]' if item['is_official'] else ''
                # docker search doesn't output this so neither will I
                #result['trusted'] = result['is_trusted']
                result['automated'] = '[OK]' if item['is_automated'] else ''
                results[star][name] = result
            # mimicking out spacing from 'docker search' command
            if not self.quiet:
                print('{0:{5}s}   {1:45s}   {2:7s}   {3:8s}   {4:10s}'.
                      format('NAME', 'DESCRIPTION', 'STARS', 'OFFICIAL', 'AUTOMATED', longest_name))
        except KeyError as _:
            die('failed to parse results fields from data returned by DockerHub ' +
                '(format may have changed?): {0}'.format(_))
        except IOError as _:
            if str(_) == '[Errno 32] Broken pipe':
                pass
            else:
                raise

        def truncate(mystr, length):
            if len(mystr) > length:
                mystr = mystr[0:length-3] + '...'
            return mystr

        for star in reversed(sorted(results)):
            for name in sorted(results[star]):
                if self.quiet:
                    print(name.encode('utf-8'))
                else:
                    desc = truncate(results[star][name]['description'], 45)
                    print('{0:{5}s}   {1:45s}   {2:<7d}   {3:8s}   {4:10s}'.
                          format(name.encode('utf-8'), desc.encode('utf-8'), star,
                                 results[star][name]['official'],
                                 results[star][name]['automated'],
                                 longest_name))
        if self.verbose and not self.quiet:
            try:
                print('\nResults Shown: {0}\nTotal Results: {1}'.format(len(data['results']), data['num_results']))
            except KeyError as _:
                die('failed to parse get total results count from data returned by DockerHub ' +
                    '(format may have changed?): {0}'.format(_))

    @staticmethod
    def search(term, limit=25):
        url = 'https://index.docker.io/v1/search?q={0}&n={1}'.format(urllib.quote_plus(term), limit)
        log.debug('GET %s' % url)
        try:
            verify = True
            # workaround for Travis CI and older pythons - we're not exchanging secret data so this is ok
            #if os.getenv('TRAVIS'):
            #    verify = False
            req = requests.get(url, verify=verify)
        except requests.exceptions.RequestException as _:
            die(_)
        log.debug("response: %s %s", req.status_code, req.reason)
        log.debug("content:\n%s\n%s\n%s", '='*80, req.content.strip(), '='*80)
        if req.status_code != 200:
            die("%s %s" % (req.status_code, req.reason))
        if not isJson(req.content):
            die('invalid non-JSON response from DockerHub!')
        if log.isEnabledFor(logging.DEBUG):
            print(jsonpp(req.content), file=sys.stderr)
            print('='*80, file=sys.stderr)
        try:
            data = json.loads(req.content)
        except KeyError as _:
            die('failed to parse output from DockerHub (format may have changed?): {0}'.format(_))
        return data


if __name__ == '__main__':
    DockerHubSearch().main()

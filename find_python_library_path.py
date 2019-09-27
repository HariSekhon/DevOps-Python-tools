#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-09-27
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

Simple tool to print the local path to one or more libraries given as arguments

Useful for finding where things are installed on different operating systems like Mac vs Linux

If no libraries are specified, finds the default library location as if the 'sys' argument was given

Tested on Python 2.7 and Python 3.x on Mac and Linux

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import getpass
import os
import sys

__author__ = 'Hari Sekhon'
__version__ = '0.3.0'

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)


def usage():
    print(__doc__.strip())
    print('\n\nusage: {} <library1> [<library2> <library3>...]\n'\
          .format(os.path.basename(sys.argv[0])), file=sys.stderr)
    sys.exit(3)

def get_module_location(module):
    # pylint: disable=wrong-import-position,import-error
    imported_module = __import__(module)
    # sys doesn't have __file__ but it does have base_prefix
    attribs = dir(imported_module)
    # - looks like 'sys.base_prefix' / 'sys.base_exec_prefix' are only available in IPython
    # - don't use 'executable' as it will point to a generic location eg. /usr/bin/python
    #   or /usr/local/opt/python/bin/python3.7) instead of the actual library path
    #   like /usr/local/Cellar/python/3.7.4_1/Frameworks/Python.framework/Versions/3.7
    #potential_attribs = ['__file__', 'exec_prefix', 'base_prefix', 'base_exec_prefix']
    potential_attribs = ['__file__', 'exec_prefix'] #, 'executable']
    for potential_attrib in potential_attribs:
        if potential_attrib in attribs:
            value = getattr(imported_module, potential_attrib)
            if potential_attrib == 'exec_prefix':
                if not 'Python.framework' in value and not 'site-packages' in value:
                    continue
            return value
    # to account for sys not having __file__ attribute
    if '__name__' in attribs and imported_module.__name__ == 'sys':
        user = getpass.getuser()
        for path in sys.path:
            # don't return local /Users/$USER/Library/Python/2.7/lib/python/site-packages
            # as that is not the source of sys
            if user in path:
                continue
            if path.endswith('/site-packages'):
                #value = path.rsplit('/site-packages')[0]
                return value
    raise AttributeError('could not find any attribute to determine location out of: {}'\
                         .format(', '.join(potential_attribs)))

def main():
    exitcode = 0
    if len(sys.argv) < 2:
        sys.argv.append('sys')
    for arg in sys.argv:
        if arg.startswith('-'):
            usage()
    for module in sys.argv[1:]:
        try:
            print(get_module_location(module))
        except AttributeError as _:
            print('attributes not found in module: {} - {}'.format(module, _), file=sys.stderr)
            exitcode = max(1, exitcode)
        except ImportError as _:
            print('module not found: {} - {}'.format(module, _), file=sys.stderr)
            exitcode = max(2, exitcode)
    sys.exit(exitcode)


if __name__ == '__main__':
    main()

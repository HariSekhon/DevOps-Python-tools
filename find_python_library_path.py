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

Simply tool to print the local path to one or more libraries given as arguments

Useful for finding where things are installed on different operating systems like Mac vs Linux

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import sys

__author__ = 'Hari Sekhon'
__version__ = '0.1.0'

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)


def usage():
    print('usage: {} <library1> [<library2> <library3>...]'.format(os.path.basename(sys.argv[0])), file=sys.stderr)
    sys.exit(3)


def main():
    exitcode = 0
    for module in sys.argv[1:]:
        try:
            # pylint: disable=wrong-import-position,import-error
            imported = __import__(module)
            # sys doesn't have __file__ but it does have base_prefix
            attribs = dir(imported)
            potential_attribs = ['__file__', 'base_prefix', 'base_exec_prefix', 'exec_prefix']
            found = False
            for _ in potential_attribs:
                if _ in attribs:
                    print(getattr(imported, _))
                    found = True
                    break
            if not found:
                raise AttributeError('could not find any attribute to determine location out of: {}'\
                                     .format(', '.join(potential_attribs)))
        except AttributeError as _:
            print('attributes not found: {} - {}'.format(module, _), file=sys.stderr)
            exitcode = max(1, exitcode)
        except ImportError as _:
            print('module not found: {} - {}'.format(module, _), file=sys.stderr)
            exitcode = max(2, exitcode)
    sys.exit(exitcode)


if __name__ == '__main__':
    main()

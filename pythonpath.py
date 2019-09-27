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

Simple tool to print the Python sys.path, one per line

Tested on Python 2.7 and Python 3.x on Mac and Linux

"""

from __future__ import print_function
#from __future__ import unicode_literals

import sys

__author__ = 'Hari Sekhon'
__version__ = '0.1.0'

#libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
#sys.path.append(libdir)


def main():
    for path in sys.path:
        if path:
            print(path)


if __name__ == '__main__':
    main()

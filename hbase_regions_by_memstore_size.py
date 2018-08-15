#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-06 10:42:59 +0100 (Thu, 06 Oct 2016)
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

Tool to find HBase Regions memstores sizes across any given RegionServers using JMX API stats

Argument list should be one or more RegionServers to dump the JMX stats from

See also hbase_regions_by_size.py
         hbase_regions_least_used.py

Tested on Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import traceback
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from hbase_regions_by_size import HBaseRegionsBySize
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.2'


class HBaseRegionsByMemstoreSize(HBaseRegionsBySize):

    def __init__(self):
        # Python 2.x
        super(HBaseRegionsByMemstoreSize, self).__init__()
        # Python 3.x
        # super().__init__()
        # could have just made this a switch to hbase_regions_by_size.py but it's easier to see as separate prog
        self.metric = 'memStoreSize'


if __name__ == '__main__':
    HBaseRegionsByMemstoreSize().main()

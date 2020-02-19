#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-11-26 10:08:52 +0000 (Tue, 26 Nov 2019)
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

Connect to an Impala daemon and print the first matching DDL metadata field (eg. 'Location')
for each table in each database, or only those matching given db / table regexes

Examples (fields are case sensitive regex and return  N/A without match):

./impala_tables_metadata.py --field Location ...
./impala_tables_metadata.py --field SerDe ...

Caveats:

    Hive is more reliable as Impala breaks on some table metadata definitions where Hive doesn't

    Impala is faster than Hive for the first ~1000 tables but then slows down
    so if you have a lot of tables I recommend you use the Hive version of this instead
    eg. by ~1900 tables the Hive version will overtake the Impala version and
    for thousands of tables Impala actuallys runs 1.5 - 2x slower than the Hive version overall

Tested on Impala 2.7.0, 2.12.0 on CDH 5.10, 5.16 with Kerberos and SSL

Due to a thrift / impyla bug this needs exactly thrift==0.9.3, see

https://github.com/cloudera/impyla/issues/286

If you get an error like this:

ERROR:impala.hiveserver2:Failed to open transport (tries_left=1)
...
TTransportException: TSocket read 0 bytes

then check your --kerberos and --ssl settings match the cluster's settings
(Thrift and Kerberos have the worst error messages ever)

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
srcdir = os.path.abspath(os.path.dirname(__file__))
pylib = os.path.join(srcdir, 'pylib')
sys.path.append(pylib)
try:
    # pylint: disable=wrong-import-position
    from hive_tables_metadata import HiveTablesMetadata
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.4.0'


class ImpalaTablesMetadata(HiveTablesMetadata):

    def __init__(self):
        # Python 2.x
        super(ImpalaTablesMetadata, self).__init__()
        # Python 3.x
        # super().__init__()

        # these are auto-set checking sys.argv[0] in HiveImpalaCLI class
        self.name = 'Impala'
        #self.default_port = 21050
        #self.default_service_name = 'impala'


if __name__ == '__main__':
    ImpalaTablesMetadata().main()

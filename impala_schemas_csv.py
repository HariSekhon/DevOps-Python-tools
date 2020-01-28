#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-11-07 14:52:38 +0000 (Thu, 07 Nov 2019)
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

Connect to an Impala daemon and dump all the schemas, tables and columns out in CSV format to stdout

In practice Hive is much more reliable than Impala for dumping masses of schema (see adjacent hive_schemas_csv.py)

Impala appears faster initially but then slows down more than Hive and hits things query handle errors
under sustained load of extracting large amounts of schema information

There is also a risk that Impala's metadata may be out of date, so Hive is strongly preferred for this


CSV format:

database,table,column,type


I recommend generating quoted csv because you may encounter Hive data types such as decimal(15,2)
which would cause incorrect field splitting, you can disable by setting --quotechar='' to blank but
if escaping is needed then you will be forced to specify an --escapechar otherwise the csv writer will
raise a traceback to tell you to set one (eg. --escapechar='\\')

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
#from __future__ import unicode_literals

from hive_schemas_csv import HiveSchemasCSV

__author__ = 'Hari Sekhon'
__version__ = '0.5.0'


class ImpalaSchemasCSV(HiveSchemasCSV):

    def __init__(self):
        # Python 2.x
        super(ImpalaSchemasCSV, self).__init__()
        # Python 3.x
        # super().__init__()

        # these are auto-set checking sys.argv[0] in HiveImpalaCLI class
        self.name = 'Impala'
        #self.default_port = 21050
        #self.default_service_name = 'impala'


if __name__ == '__main__':
    ImpalaSchemasCSV().main()

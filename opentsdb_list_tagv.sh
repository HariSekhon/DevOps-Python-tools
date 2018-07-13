#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-07-13 22:36:14 +0100 (Fri, 13 Jul 2018)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

# Quick script to list OpenTSDB metrics via local HBase Shell

# Tested on OpenTSDB 2.3 on HBase 1.4

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

if ! which hbase &>/dev/null; then
    echo "hbase command not found in \$PATH ($PATH)"
    exit 1
fi

hbase shell <<< "scan 'tsdb-uid', { COLUMNS => 'name:tagv', VERSIONS => 1 }" 2>/dev/null |
grep 'value=' |
sed 's/^.*, value=//' |
sort -u

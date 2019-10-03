#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-07-11 19:26:21 +0100 (Wed, 11 Jul 2018)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

# Find regions that require major_compact after region migration to achieve data locality again
#
# Tested on Hortonworks HDP 2.6 (HBase 1.1.2) and Apache HBase 1.3.1

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

usage(){
    echo "usage: $0 <list of regionservers>"
    exit 1
}

port="${REGIONSERVER_PORT:-16030}"

if [ $# -lt 1 ]; then
    usage
fi

for server in "$@"; do
    curl -s "$server:$port/jmx" |
    grep 'compactionsCompletedCount"[[:space:]]*:[[:space:]]*0,$' |
    sed 's/.*_table_//; s/_region_/ /; s/_metric_.*//' |
    column -t
done

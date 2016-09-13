#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-13 09:17:01 +0200 (Tue, 13 Sep 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

DESCRIPTION="Script to flush HBase tables

Takes an optional regex selection, otherwise flushes all HBase tables

Uses HBase Shell which must be in the \$PATH

Written to flush OpenTSDB tables before shutdown as the bulk import tool is using Durability.SKIP_WAL

Tested on Hortonworks HDP 2.3 (HBase 1.1.2) and Apache HBase 1.2.2

"

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

srcdir="$(cd "$(dirname "$0")" && pwd)"

die(){
    echo "$@"
    exit 1
}

usage(){
    die "${DESCRIPTION}usage: $0 [table_regex]
"
}

for x in $@; do
    case $x in
         -*) usage
            ;;
    esac
done

regex="${1:-.*}"

output="$(hbase shell <<< 'list')"

tables="$(sed -n '/TABLE/,/row.*[[:space:]]in[[:space:]].*[[:space:]]seconds/p' <<< "$output" | sed '/^TABLE$/d ; $d')"

[ -z "$tables" ] && die "No Tables Found"

tables_to_flush="$(egrep "$regex" <<< "$tables")"

[ -z "$tables_to_flush" ] && die "No Tables Found Matching the given regex '$regex'"

echo "Flushing the following tables:

$tables_to_flush
"

sed "s/^[[:space:]]*/flush '/; s/[[:space:]]*$/'/" <<< "$tables_to_flush" |
hbase shell

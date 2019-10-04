#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-06-29 19:01:22 +0100 (Fri, 29 Jun 2018)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

usage(){
    [ -n "${*:-}" ] && echo "$@"
    echo
    echo "Fast and dirty script to scan an HBase table to determine all columns (column family + qualifiers)

Beware this is a very expensive O(n) operation and you shouldn't be doing this unless you know what you're doing

usage: $0 --table <tablename>
usage: $0 -t <tablename>
"
    exit 1
}

until [ $# -lt 1 ]; do
    case $1 in
        -t|--table)
            table="$2"
            shift || :
            ;;
         *) usage
            ;;
    esac
    shift
done

if [ -z "${table:-}" ]; then
    usage "ERROR: Table not defined, use --table switch"
fi

if ! type -P hbase &>/dev/null; then
    usage "ERROR: hbase command not found in \$PATH ($PATH)"
fi

hbase shell <<< "scan '$table'" |
sed 's/.*columns=//;s/,.*$//' |
grep -v -e ^$ -e [[:space:]] |
sort -u

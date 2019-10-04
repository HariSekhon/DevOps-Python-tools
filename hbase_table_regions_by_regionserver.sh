#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-08-24 19:34:33 +0100 (Fri, 24 Aug 2018)
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

regionservers=""
port="${HBASE_REGIONSERVER_PORT:-16030}"

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    cat <<EOF
Quick script to output region counts per table across RegionServers using the RegionServers JMX API


Tested on HBase 1.3


usage: ${0##*/} [options] regionserver1 regionserver2 regionserver3 ...

       ${0##*/} [options] regionserver{1..100}

-T --table  Table to filter (regex)
-p --port   RegionServer HTTP JMX port

EOF
    exit 3
}

table=".*"
until [ $# -lt 1 ]; do
    case $1 in
   -T|--table)  table="${2:-}"
                shift || :
                ;;
    -p|--port)  port="${2:-$port}"
                shift || :
                ;;
    -h|--help)  usage
                ;;
            *)  regionservers="$regionservers $1"
                ;;
    esac
    shift || :
done

if [ -z "$regionservers" ]; then
    usage "regionservers not defined, must supply arguments of regionservers hosts"
fi

check_bin(){
    local bin="$1"
    # shellcheck disable=SC2230
    if ! type -P "$bin" &>/dev/null; then
        echo "'$bin' command not found in \$PATH ($PATH)"
        exit 1
    fi
}
check_bin curl

curl_options=""
if [ -z "${DEBUG:-}" ]; then
    curl_options="$curl_options -s"
fi
for regionserver in $(tr ' ' '\n' <<< "$regionservers" | sort -u); do
    echo "$regionserver:"
    # shellcheck disable=SC2086
    curl $curl_options "$regionserver:$port/jmx" |
    grep "_table_.*${table}.*_region_" |
    sed 's/.*_table_//; s/_region_/ /; s/_.*$//' |
    sort -u |
    awk '{print $1}' |
    uniq -c |
    sort -k1nr ||
    curl ${curl_options% -s} "$regionserver:$port/jmx"
    echo
done

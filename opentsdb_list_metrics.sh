#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-07-13 22:36:14 +0100 (Fri, 13 Jul 2018)
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

tsd_url="http://localhost:4242"
metrics="metrics"

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    cat <<EOF
Quick script to list OpenTSDB metrics via OpenTSDB Suggest API

Metrics output - one metric per line

Tested on OpenTSDB 2.3 on HBase 1.4

See also opentsdb_list_metrics_hbase.sh - this version is 6-9x faster but that version can show metrics registered dates ordered by date as that info isn't returned by the OpenTSDB Suggest API


usage: ${0##*/} [options] <curl_options>

-T --tsd    TSD url (default: http://localhost:4242)
--tagk      List tagk values (default lists metrics)
--tagv      List tagv values (default lists metrics, mutually exclusive with --tagk)

EOF
    exit 1
}

set_metric_type(){
    if [ "$metrics" != "metrics" ]; then
        usage "--tagk and --tagv are mutually exclusive!"
    fi
    metrics="$1"
}

curl_options=""
until [ $# -lt 1 ]; do
    case $1 in
     -T|--tsd)  tsd_url="${2:-}"
                shift || :
                ;;
       --tagk)  set_metric_type tagk
                ;;
       --tagv)  set_metric_type tagv
                ;;
    -h|--help)  usage
                ;;
            *)  #usage "unknown argument: $1"
                curl_options="$curl_options $1"
                ;;
    esac
    shift || :
done

check_bin(){
    local bin="$1"
    if ! type -P "$bin" &>/dev/null; then
        echo "'$bin' command not found in \$PATH ($PATH)"
        exit 1
    fi
}
check_bin curl
check_bin jq

if [ -z "${DEBUG:-}" ]; then
    curl_options="$curl_options -s"
fi
# split opts
# shellcheck disable=SC2086
curl $curl_options "$tsd_url/api/suggest?type=$metrics&q=&max=2000000000" |
jq '.[]' |
sed 's/"//g' |
sort ||
# this is here mainly just to output the error message without DEBUG=1 mode being necessary
curl ${curl_options% -s} "$tsd_url/api/suggest?type=$metrics&q=&max=2000000000"

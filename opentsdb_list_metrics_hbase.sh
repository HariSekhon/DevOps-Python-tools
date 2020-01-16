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

PATH="$PATH:/opt/hbase/bin:/hbase/bin"

metrics="metrics"
by_age=0

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    cat <<EOF
Quick script to list OpenTSDB metrics via local HBase Shell

Metrics output - one metric per line

Metrics By Age - output:

<timestamp_epoch_millis>  <human_timestamp>   <metric>

Tested on OpenTSDB 2.3 on HBase 1.4


usage: ${0##*/} [options]

--tagk      List tagk values (default lists metrics)
--tagv      List tagv values (default lists metrics, mutually exclusive with --tagk)
--by-age    List by age, oldest first with epoch, human time and metric columns

EOF
    exit 1
}

set_metric_type(){
    if [ "$metrics" != "metrics" ]; then
        usage "--tagk and --tagv are mutually exclusive!"
    fi
    metrics="$1"
}

until [ $# -lt 1 ]; do
    case $1 in
       --tagk)  set_metric_type tagk
                ;;
       --tagv)  set_metric_type tagv
                ;;
     --by-age)  by_age=1
                ;;
    -h|--help)  usage
                ;;
            *)  usage "unknown argument: $1"
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
check_bin hbase
check_bin python

print_metrics(){
    hbase shell <<< "scan 'tsdb-uid', { COLUMNS => 'name:$metrics', VERSIONS => 1 }" 2>/dev/null |
    grep 'value=' |
    sed 's/^.*, value=//' |
    sort -u
}

print_metrics_by_age(){
    # hackish but convenient - forking to the date command thousands or hundreds of thousands of times can take hours, python takes 10 secs even for 250,000+ metrics
    tmp_python_script=$(mktemp)
    cat > "$tmp_python_script" <<EOF
from __future__ import print_function
import sys, time
metrics = {}
for line in sys.stdin:
    try:
        (ts, metric) = line.split()
    except ValueError as _:
        print('ValueError: {}, line: {}'.format(_, line), file=sys.stderr)
#    if  metric not in metrics or ts < metrics[metric]:
#        metric[metric] = ts
#for metric in metrics:
#    ts = metrics[metric]
    print("{}\t{}\t{}".format(ts, time.strftime("%F %T", time.localtime(int(ts)/1000)), metric))
EOF
    # shellcheck disable=SC2064
    trap "rm '$tmp_python_script'" EXIT

    hbase shell <<< "scan 'tsdb-uid', { COLUMNS => 'name:$metrics', VERSIONS => 1 }" 2>/dev/null |
    grep 'value=' |
    sed 's/^.*, timestamp=//; s/, value=/ /' |
    python "$tmp_python_script" |
    sort -k1n
}

if [ $by_age = 0 ]; then
    print_metrics
else
    print_metrics_by_age
fi

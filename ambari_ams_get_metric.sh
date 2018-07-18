#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-07-16 22:14:34 +0100 (Mon, 16 Jul 2018)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

ams_host="${AMBARI_METRICS_COLLECTOR_HOST:-${AMBARI_HOST:-${HOST:-}}}"
ams_port="${AMBARI_METRICS_COLLECTOR_PORT:-${AMBARI_PORT:-${PORT:-6188}}}"
metric=""
node=""

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    cat <<EOF
Fetches a given Ambari Metric from the Ambari Metrics Collector API

usage: ${0##*/} [options]

-H  --host      Ambari Metrics Collector host (\$AMBARI_METRICS_COLLECTOR_HOST, \$AMBARI_HOST, \$HOST)
-P  --port      Ambari Metrics Collector port (default: 6188, \$AMBARI_METRICS_COLLECTOR_PORT, \$AMBARI_PORT, \$PORT)
-m  --metric    The metric to fetch (see ./ambari_ams_list_metrics.sh for a list of available metrics)
-n  --node      Cluster node hostname to fetch metric for (see ./ambari_ams_list_hosts.sh for a list of available hosts)
EOF
    exit 1
}

until [ $# -lt 1 ]; do
    case $1 in
    -H|--host)  ams_host="${2:-}"
                shift
                ;;
    -P|--port)  ams_host="${2:-}"
                shift
                ;;
  -m|--metric)  metric="${2:-}"
                shift
                ;;
    -n|--node)  node="${2:-}"
                shift
                ;;
    -h|--help)  usage
                ;;
            *)  usage "unknown argument: $1"
                ;;
    esac
    shift
done

if [ -z "$ams_host" ]; then
    usage "--host not defined"
elif [ -z "$ams_port" ]; then
    usage "--port not defined"
elif [ -z "$metric" ]; then
    usage "--metric not defined"
elif [ -z "$node" ]; then
    usage "--node not defined"
fi

check_bin(){
    local bin="$1"
    if ! which $bin &>/dev/null; then
        echo "$bin command not found in \$PATH ($PATH)"
        exit 1
    fi
}
check_bin curl
check_bin python

# returns last metric with second precision
curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics?metricNames=$metric&hostname=$node" |
python -m json.tool ||
    { echo "You probably specified an invalid / non-existent --metric and --node combination to wrong --host/--port"; exit 2; }

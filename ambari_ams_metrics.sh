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

# There were 2346 metrics last I checked but this probably varies a lot based on what services are deployed

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

ams_host="${AMBARI_METRICS_COLLECTOR_HOST:-${AMBARI_HOST:-${HOST:-}}}"
ams_port="${AMBARI_METRICS_COLLECTOR_PORT:-${AMBARI_PORT:-${PORT:-6188}}}"
list_nodes=false
metric=""
node=""

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    cat <<EOF
Script to making it easy to test the Ambari Metrics Collector API

Performs one of the following actions:

- List all metrics collected by AMS Collector (default action if --list-hosts or --metric isn't specified)
- List all hosts which have metrics collected by AMS Collector
- Fetch a given Ambari Metric for a given host

usage: ${0##*/} [options]

-H  --host          Ambari Metrics Collector host (\$AMBARI_METRICS_COLLECTOR_HOST, \$AMBARI_HOST, \$HOST)
-P  --port          Ambari Metrics Collector port (default: 6188, \$AMBARI_METRICS_COLLECTOR_PORT, \$AMBARI_PORT, \$PORT)
    --list-metrics  List all metrics collected by AMS (default action)
-o  --list-hosts    List all hosts for which metrics collected by AMS
-m  --metric        Fetch metric for given node
-n  --node          Cluster node hostname to fetch metric for
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
   --list-metrics)  :
                    ;;
  -o|--list-nodes)  list_nodes=true
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
    shift || :
done

if [ -z "$ams_host" ]; then
    usage "--host not defined"
elif [ -z "$ams_port" ]; then
    usage "--port not defined"
fi
if [ -n "$metric" ]; then
    if [ -z "$node" ]; then
        usage "--node must be defined when using --metric"
    fi
elif [ -n "$node" ]; then
    usage "--node option requires --metric. Use --list-metrics"
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

list_metrics(){
    curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics/metadata" |
    python -m json.tool |
    grep metricname |
    awk '{print $2}' |
    sed 's/"//g;s/,$//' |
    sort -u ||
        { echo "You probably specified the wrong --host/--port"; exit 2; }
}

list_hosts(){
    curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics/hosts" |
    python -m json.tool |
    egrep '^[[:space:]]*".+":[[:space:]]* \[[[:space:]]*$' |
    sed 's/"//g;s/:.*//;s/[[:space:]]*//g' |
    grep -v fakehostname |
    sort ||
        { echo "You probably specified the wrong --host/--port"; exit 2; }
}

fetch_metric(){
    # returns last metric with second precision
    curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics?metricNames=$metric&hostname=$node" |
    python -m json.tool ||
        { echo "You probably specified an invalid / non-existent --metric and --node combination to wrong --host/--port"; exit 2; }
}

if [ "$list_nodes" = true ]; then
    list_hosts
elif [ -n "$metric" ]; then
    fetch_metric
else
    list_metrics
fi

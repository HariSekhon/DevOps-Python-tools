#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-07-16 22:14:34 +0100 (Mon, 16 Jul 2018)
#
#  https://github.com/harisekhon/devops-python-tools
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
list_metrics=false
list_nodes=false
metric=""
node_list=""

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    cat <<EOF
Script to making it easy to test the Ambari Metrics Collector API

Performs one of the following actions:

- List all metrics collected by AMS Collector (default action if --list-hosts or --metric isn't specified)
- List all cluster nodes for which metrics have been collected by AMS
- Fetch a given Ambari Metric for given cluster node(s)

Tested on Ambari 2.5, 2.6 on HDP 2.6

export AMBARI_METRICS_COLLECTOR_HOST=myhost  # or use --host each time if you prefer but it's longer
./${0##*/} --list-metrics
./${0##*/} --list-nodes
./${0##*/} --metric <blah> --nodes master1,master2  # comma separated list
./${0##*/} --metric <blah> --nodes datanode{1..10}  # makes use of args being incorporated to node list


usage: ${0##*/} [options]

-H  --host          Ambari Metrics Collector host (\$AMBARI_METRICS_COLLECTOR_HOST, \$AMBARI_HOST, \$HOST)
-P  --port          Ambari Metrics Collector port (default: 6188, \$AMBARI_METRICS_COLLECTOR_PORT, \$AMBARI_PORT, \$PORT)
    --list-metrics  List all metrics collected by AMS (default action)
-o  --list-nodes    List all cluster nodes for which metrics have been collected by AMS
-m  --metric        Fetch metric for given node(s)
-n  --nodes         Specify nodes for which to fetch given --metric (comma separated list, arguments are added to the node list)
-D  --debug         Debug mode
EOF
    exit 1
}

until [ $# -lt 1 ]; do
    case $1 in
        -H|--host)  ams_host="${2:-}"
                    shift || :
                    ;;
        -P|--port)  ams_host="${2:-}"
                    shift || :
                    ;;
   --list-metrics)  list_metrics=true
                    [ "$list_nodes" = true ] && usage '--list-metrics and --list-nodes are mutually exclusive!'
                    ;;
  -o|--list-nodes)  list_nodes=true
                    [ "$list_metrics" = true ] && usage '--list-metrics and --list-nodes are mutually exclusive!'
                    ;;
      -m|--metric)  metric="${2:-}"
                    shift || :
                    ;;
-n|--node|--nodes)  node_list="${2:-}"
                    shift || :
                    ;;
        -h|--help)  usage
                    ;;
       -D|--debug)  DEBUG=1; set -x
                    ;;
               -*)  usage "unknown option: $1"
                    ;;
                *)  node_list="$node_list $1"
                    ;;
    esac
    shift || :
done

if [ -z "$ams_host" ]; then
    usage "--host not defined"
elif [ -z "$ams_port" ]; then
    usage "--port not defined"
fi
if [ -n "$node_list" ] && [ -z "$metric" ]; then
    usage "--nodes option requires --metric. See --list-metrics for a list of available metrics"
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
    grep -E '^[[:space:]]*".+":[[:space:]]* \[[[:space:]]*$' |
    sed 's/"//g;s/:.*//;s/[[:space:]]*//g' |
    grep -v fakehostname |
    sort ||
        { echo "You probably specified the wrong --host/--port"; exit 2; }
}

fetch_metric(){
    local node="$1"
    # returns last metric with second precision
    curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics?metricNames=$metric&hostname=$node" |
    python -m json.tool ||
        { echo "You probably specified an invalid / non-existent --metric and --nodes combination to wrong --host/--port"; exit 2; }
}

fetch_metrics(){
    node_list="$(tr ',' ' ' <<< "$node_list")"
    if [ -z "$node_list" ]; then
        node_list=$(list_hosts)
    fi
    for node in $node_list; do
        fetch_metric "$node"
    done
}

if [ "$list_nodes" = true ]; then
    list_hosts
elif [ -n "$metric" ]; then
    fetch_metrics
else
    list_metrics
fi

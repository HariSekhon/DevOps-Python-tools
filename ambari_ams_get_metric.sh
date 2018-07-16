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

if [ $# != 3 ]; then
    echo "Fetches a given Ambari Metric from the Ambari Metrics Collector API

usage: ${0##*/} <ambari_metrics_collector_host> <metric> <cluster_node_hostname>

See also ./ambari_ams_list_metrics.sh - find available metrics
         ./ambari_ams_list_hosts.sh   - find available hosts
"
    exit 1
fi

ams_host="$1"
ams_port="${AMBARI_METRICS_COLLECTOR_PORT:-${AMBARI_PORT:6188}}"
metric="$2"
host="$3"

# returns last metric with second precision
curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics?metricNames=$metric&hostname=$host" |
python -m json.tool

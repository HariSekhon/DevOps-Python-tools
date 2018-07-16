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

# There were 2345 metrics last I checked but this probably varies a lot based on what services are deployed

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

if [ $# != 1 ]; then
    echo "Lists all hosts in Ambari Metrics Collector service via the API

usage: ${0##*/} <ambari_metrics_collector_host>
"
    exit 1
fi

ams_host="$1"
ams_port="${AMBARI_METRICS_COLLECTOR_PORT:-${AMBARI_PORT:6188}}"

curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics/metadata" |
python -m json.tool |
grep metricname |
awk '{print $2}' |
sed 's/"//g;s/,$//' |
sort -u

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

ams_host="${AMBARI_METRICS_COLLECTOR_HOST:-${AMBARI_HOST:-${HOST:-}}}"
ams_port="${AMBARI_METRICS_COLLECTOR_PORT:-${AMBARI_PORT:-${PORT:-6188}}}"

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    echo "Lists all metrics in Ambari Metrics Collector service via the API

usage: ${0##*/} [options]

-H  --host      Ambari Metrics Collector host (\$AMBARI_METRICS_COLLECTOR_HOST, \$AMBARI_HOST, \$HOST)
-P  --port      Ambari Metrics Collector port (default: 6188, \$AMBARI_METRICS_COLLECTOR_PORT, \$AMBARI_PORT, \$PORT)
"
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

curl -s "$ams_host:$ams_port/ws/v1/timeline/metrics/metadata" |
python -m json.tool |
grep metricname |
awk '{print $2}' |
sed 's/"//g;s/,$//' |
sort -u ||
    { echo "You probably specified the wrong --host/--port"; exit 2; }

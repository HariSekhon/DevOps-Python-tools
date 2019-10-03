#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-27 17:25:36 +0100 (Tue, 27 Sep 2016)
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

AMBARI_HOST="${1:-${AMBARI_HOST:-localhost}}"
AMBARI_PORT="${2:-${AMBARI_PORT:-8080}}"
AMBARI_USER="${3:-${AMBARI_USER:-admin}}"
AMBARI_PASSWORD="${4:-${AMBARI_PASSWORD:-admin}}"
AMBARI_CLUSTER="${5:-${AMBARI_CLUSTER:-Sandbox}}"
PROTOCOL="http"
if [ -n "${SSL:-}" ]; then
    PROTOCOL="https"
    if [ "$AMBARI_PORT" = "8080" ]; then
        AMBARI_PORT=8443
    fi
fi

usage(){
    echo "Simple script to cancel all Ambari op requests

usage: ${0##*/} <ambari_host> <ambari_port> <username> <password> <cluster_name>

Prefer using the following environment variables instead of arguments in order to not expose the Ambari admin credentials in the process list:

AMBARI_HOST         (default: localhost)
AMBARI_PORT         (default: 8080)
AMBARI_USER         (default: admin)
AMBARI_PASSWORD     (default: admin)
AMBARI_CLUSTER      (default: Sandbox)
SSL                 (default: blank, any value enables SSL)
"
    exit 1
}

if [ $# -gt 5 ]; then
    usage
fi

echo "querying Ambari for request IDs"
curl -u "$AMBARI_USER:$AMBARI_PASSWORD" "$PROTOCOL://$AMBARI_HOST:$AMBARI_PORT/api/v1/clusters/$AMBARI_CLUSTER/requests" |
grep id |
awk '{print $3}' |
while read -r id; do
    echo "requesting cancellation of request $id"
    # Unfortunately this call returns 200 OK even if your user account doesn't have permission to do this operation, but will fail on the requests query above for wrong username/password
    curl -u "$AMBARI_USER:$AMBARI_PASSWORD" -i -H "X-Requested-By: $AMBARI_USER ($USER)" -X PUT -d '{"Requests":{"request_status":"ABORTED","abort_reason":"Aborted by user"}}' "$PROTOCOL://$AMBARI_HOST:$AMBARI_PORT/api/v1/clusters/$AMBARI_CLUSTER/requests/$id"
done

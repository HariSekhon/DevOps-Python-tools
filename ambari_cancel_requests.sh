#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-27 17:25:36 +0100 (Tue, 27 Sep 2016)
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

AMBARI_HOST="${AMBARI_HOST:-localhost}"
AMBARI_PORT="${AMBARI_PORT:-8080}"
AMBARI_USER="${AMBARI_USER:-admin}"
AMBARI_PASSWORD="${AMBARI_PASSWORD:-admin}"
AMBARI_CLUSTER="${AMBARI_CLUSTER:-Sandbox}"

echo "querying Ambari for request IDs"
curl -u $AMBARI_USER:$AMBARI_PASSWORD http://$AMBARI_HOST:$AMBARI_PORT/api/v1/clusters/$AMBARI_CLUSTER/requests |
grep id |
awk '{print $3}' |
while read id; do
    echo "requesting cancellation of request $id"
    curl -u $AMBARI_USER:$AMBARI_PASSWORD -i -H "X-Requested-By: $AMBARI_USER ($USER)" -X PUT -d '{"Requests":{"request_status":"ABORTED","abort_reason":"Aborted by user"}}' http://$AMBARI_HOST:$AMBARI_PORT/api/v1/clusters/$AMBARI_CLUSTER/requests/$id
done

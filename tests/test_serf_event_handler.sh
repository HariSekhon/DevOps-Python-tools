#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-16 16:35:51 +0000 (Sat, 16 Jan 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/.."

# shellcheck disable=SC1091
. "tests/utils.sh"

# shellcheck disable=SC1091
. "bash-tools/lib/utils.sh"

section "Testing Serf Event Handler"

check 'SERF_EVENT="query" SERF_QUERY_NAME="uptime" ./serf_event_handler.py --cmd-passthru -D < /dev/null | grep "load average"' "Serf Event Handler"

check 'echo "myData" | SERF_EVENT="query" SERF_QUERY_NAME="uptime" ./serf_event_handler.py --cmd-passthru -D 2>&1 | grep "data:[[:space:]]myData"' "Serf Event Handler with data"

echo
echo

#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-16 16:35:51 +0000 (Sat, 16 Jan 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/.."

. "tests/utils.sh"

. "bash-tools/utils.sh"

section "Testing Serf Event Handler"

check 'SERF_EVENT="query" SERF_QUERY_NAME="uptime" ./serf_event_handler.py --cmd-passthru -D < /dev/null | grep "user.*load average"' "Serf Event Handler"

check 'echo "myData" | SERF_EVENT="query" SERF_QUERY_NAME="uptime" ./serf_event_handler.py --cmd-passthru -D 2>&1 | grep "data:[[:space:]]myData"' "Serf Event Handler with data"

echo
echo

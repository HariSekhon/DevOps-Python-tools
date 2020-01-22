#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-11-20 15:35:37 +0000 (Sun, 20 Nov 2016)
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
srcdir="$(cd "$(dirname "$0")" && pwd)"

cd "$srcdir/.."

# shellcheck disable=SC1091
. ./bash-tools/lib/utils.sh

section "Getent"

start_time="$(start_timer "find_active_server.py test")"

system="$(uname -s)"
echo "system = $system"
hr

if [ "$system" = "Linux" ] ||
   [ "$system" = Darwin ]; then
    run ./getent.py passwd | grep -v ':[x*!]*:'
    # counter is lost in subshell, increment manually
    run++

    # $USER isn't always available in docker containers, use 'id' instead
    run ./getent.py passwd "$(id -un)"

    run_fail 2 ./getent.py passwd nonexistentuser

    run ./getent.py group | grep -v ':[x*!]:'
    run++

    run ./getent.py group "$(id -gn)"

    run_fail 2 ./getent.py group nonexistentgroup

    echo
    # $run_count defined in lib
    # shellcheck disable=SC2154
    echo "Tests run: $run_count"
    time_taken "$start_time" "find_active_server.py tests completed in"
else
    echo "system is not Linux or Mac, skipping..."
fi

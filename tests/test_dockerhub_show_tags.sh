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

section "Testing DockerHub Show Tags"

start_time="$(start_timer "DockerHub Show Tags")"

run ./dockerhub_show_tags.py centos debian
run ./dockerhub_show_tags.py harisekhon/centos-java
run_grep '6.7' ./dockerhub_show_tags.py centos

run_grep "^latest$" ./dockerhub_show_tags.py -q centos

run_grep "^centos6.9$" ./dockerhub_show_tags.py -q centos

echo
echo
echo "All DockerHub Show Tags tests completed successfully"
echo
# $run_count defined in lib
# shellcheck disable=SC2154
echo "Total Tests run: $run_count"
time_taken "$start_time" "DockerHub Show Tags tests completed in"
echo
echo

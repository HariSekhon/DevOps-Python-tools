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

check './dockerhub_search.py centos' "DockerHub Search for CentOS"
check './dockerhub_search.py harisekhon' "DockerHub Search for harisekhon"
check './dockerhub_search.py harisekhon -l 30' "DockerHub Search for harisekhon -l 30"
# this no longer works, API must have changed
#check './dockerhub_search.py harisekhon/hadoop-dev | grep harisekhon/hadoop-dev' "DockerHub Search for harisekhon/hadoop-dev"
check './dockerhub_search.py hadoop-dev | grep harisekhon/hadoop-dev' "DockerHub Search for harisekhon/hadoop-dev"
# causes IOError: [Errno 32] Broken pipe
#unset PYTHONUNBUFFERED
# shellcheck disable=SC2016
check '[ $(./dockerhub_search.py -q harisekhon | head -n 40 | tee /dev/stderr | grep "^harisekhon/[A-Za-z0-9_-]*$" | wc -l) = 40 ]' "DockerHub Search quiet mode for shell scripting"

echo
echo

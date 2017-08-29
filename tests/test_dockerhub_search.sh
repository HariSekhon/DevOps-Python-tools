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
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/.."

. "tests/utils.sh"

. "bash-tools/utils.sh"

section "Testing DockerHub Show Tags"

check './dockerhub_search.py centos' "DockerHub Search for CentOS"
check './dockerhub_search.py harisekhon' "DockerHub Search for harisekhon"
check './dockerhub_search.py harisekhon -n 30' "DockerHub Search for harisekhon -n 30"
check './dockerhub_search.py harisekhon/hadoop-dev | grep harisekhon/hadoop-dev' "DockerHub Search for harisekhon/hadoop-dev"
check '[ $(./dockerhub_search.py -q harisekhon | head -n 40 | grep "^harisekhon/[A-Za-z0-9-]*$" | wc -l) = 40 ]' "DockerHub Search quiet mode for shell scripting"

echo
echo

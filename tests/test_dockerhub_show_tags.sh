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

check './dockerhub_show_tags.py centos debian' "DockerHub Show Tags for CentOS & Debian"
check './dockerhub_show_tags.py centos | grep "6.7"' "DockerHub Show Tags search for CentOS 6.7 tag"

echo
echo

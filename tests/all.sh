#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-05 23:29:15 +0000 (Thu, 05 Nov 2015)
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

. "$srcdir/utils.sh"

# imported by utils.sh above
#. "$srcdir/../bash-tools/utils.sh"

export PROJECT=pytools

section "Running PyTools ALL"

# runs against . by default
cd "$srcdir/..";
bash-tools/all.sh

exit 0

bash-tools/run_tests.sh

# do help afterwards for Spark to be downloaded, and then help will find and use downloaded spark for SPARK_HOME
tests/help.sh

#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-02-26 14:40:53 +0000 (Tue, 26 Feb 2019)
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

cfg="$srcdir/../.yamllint"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

section "Running Yaml lint"

yamllint -c "$cfg" .

echo "======="
echo "SUCCESS"
echo "======="

echo
echo

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

section "Testing Git check branches upstream"

if type -P git &>/dev/null; then
    if ! [ -d Dockerfiles ]; then
        git clone https://github.com/harisekhon/Dockerfiles
    else
        pushd Dockerfiles
        git pull
        popd
    fi
fi
# TODO: check if this works later and re-enable
# https://github.com/gitpython-developers/GitPython/issues/687
if is_travis; then
    echo "WARNING: Skipping check on Travis CI due to bug in GitPython"
    exit 0
fi
if [ -d Dockerfiles ]; then
    check './git_check_branches_upstream.py . Dockerfiles' "Git check branches upstream of local repo and Dockerfiles submodule"
else
    echo "WARNING: Dockerfiles not present and git command not found to clone from github, skipping test"
fi

echo
echo

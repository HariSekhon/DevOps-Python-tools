#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-11-20 15:35:37 +0000 (Sun, 20 Nov 2016)
#
#  https://github.com/harisekhon/pytools
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

. ./bash-tools/utils.sh

section "Getent"

system=`uname -s`
echo "system = $system"
hr
if [ "$system" = "Linux" -o "$system" = Darwin ]; then
    ./getent.py passwd
    hr
    # $USER isn't always available in docker containers, use 'id' instead
    ./getent.py passwd `id -un`
    hr
    ./getent.py group
    hr
    ./getent.py group `id -gn`
    hr
else
    echo "system is not Linux or Mac, skipping..."
fi

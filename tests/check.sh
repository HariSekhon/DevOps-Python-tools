#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-16 16:47:43 +0000 (Sat, 16 Jan 2016)
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

check(){
    cmd=$1
    msg=$2
    echo
    hr2
    echo "$msg"
    hr2
    echo
    echo "cmd:  $cmd"
    echo
    if eval "$cmd"; then
        echo
        echo "SUCCESS"
    else
        echo
        echo "FAILED"
        exit 1
    fi
    echo
}

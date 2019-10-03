#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-08-29 14:57:23 +0200 (Tue, 29 Aug 2017)
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

srcdir="$(dirname "$0")"

docker_image="${1:-}"

if [ -z "$docker_image" ]; then
    echo "usage: $0 <repo>"
    exit 1
fi

for tag in $("$srcdir/dockerhub_show_tags.py" -q "$docker_image"); do
    echo "docker pull $docker_image:$tag"
    docker pull "$docker_image:$tag"
    echo
done

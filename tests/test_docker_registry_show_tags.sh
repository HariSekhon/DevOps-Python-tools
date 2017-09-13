#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-09-12 17:49:29 +0200 (Tue, 12 Sep 2017)
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

section "Testing Docker Registry Show Tags"

exit 0

check_docker_available

export DOCKER_REGISTRY_HOST="${DOCKER_HOST:-localhost}"
export DOCKER_REGISTRY_HOST="${DOCKER_REGISTRY_HOST/*:\/\/}"
export DOCKER_REGISTRY_HOST="${DOCKER_REGISTRY_HOST/:*}"

export DOCKER_REGISTRY_PORT=5000

export DOCKER_SERVICE="pytools-registry-test"
export COMPOSE_FILE="$srcdir/docker/registry-docker-compose.yml"

max_secs=30

#name="registry-docker-show-tags-test"

cd "$srcdir/docker"
openssl genrsa -out registry.key 2048
yes "" | openssl req -new -key registry.key -out registry.csr || :
openssl x509 -req -days 3650 -in registry.csr -signkey registry.key -out registry.crt
cd "$srcdir/../.."

#docker run -d --name "$name" -p 5000:5000 registry:2
docker-compose --verbose up -d

when_ports_available "$max_secs" "$DOCKER_REGISTRY_HOST" "$DOCKER_REGISTRY_PORT"

#export DOCKER_REGISTRY_PORT="$(docker-compose port "docker_${DOCKER_SERVICE}_1" "$DOCKER_REGISTRY_PORT" | sed 's/.*://')"
export DOCKER_REGISTRY_PORT="$(docker port "docker_${DOCKER_SERVICE}_1" "$DOCKER_REGISTRY_PORT" | sed 's/.*://')"

if [ -z "$DOCKER_REGISTRY_PORT" ]; then
    echo "DOCKER_REGISTRY_PORT not found from running container, did container fail to start up properly?"
    exit 1
fi

tag="0.7"
repo1="harisekhon/nagios-plugin-kafka"
repo2="harisekhon/consul:$tag"

for image in $repo1 $repo2; do
    docker pull "$image"
    docker tag "$image" "$DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT/$image"
    # cannot specify http:// or https:// - docker will infer the respository from the tag prefix
    docker push "$DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT/$image"
done

check "./docker_registry_show_tags.py $repo1 $repo2 harisekhon/centos-java" "Docker Registry Show Tags for $repo1 & $repo2"
check "./docker_registry_show_tags.py $repo2" "Docker Registry Show Tags for $repo2"
check "./docker_registry_show_tags.py $repo2 | grep '$tag'" "Docker Registry Show Tags search for $repo2 tag $tag"

#docker rm -f "$name"
#docker-compose down

echo
echo "Docker Registry Show Tags tests passed successfully"
echo
echo

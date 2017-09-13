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

check_docker_available

export DOCKER_REGISTRY_HOST="${DOCKER_HOST:-localhost}"
export DOCKER_REGISTRY_HOST="${DOCKER_REGISTRY_HOST/*:\/\/}"
export DOCKER_REGISTRY_HOST="${DOCKER_REGISTRY_HOST/:*}"

export DOCKER_REGISTRY_PORT=5000

export DOCKER_SERVICE="pytools-registry-test"
export COMPOSE_FILE="$srcdir/docker/registry-docker-compose.yml"

max_secs=30

#name="registry-docker-show-tags-test"

#if is_travis; then
#    if sudo grep insecure-registries /etc/docker/daemon.json; then
#        echo "insecure registries setting already found in /etc/docker/daemon.json, you may need to modify this manually otherwise tests may fail"
#    else
#        echo "addeding insecure registries localhost:5000 to /etc/docker/daemon.json"
#        if [ -s /etc/docker/daemon.json ]; then
#            sudo perl -e 's/}/, "insecure-registries": ["localhost:5000"] }/' /etc/docker/daemon.json
#        else
#            sudo bash <<EOF
#            echo '{ "insecure-registries": ["localhost:5000"] }' >> /etc/docker/daemon.json
#EOF
#        fi
#        echo
#        echo "restarting Docker"
#        sudo service docker restart
#    fi
#else
#    echo "WARNING: you may need to enable insecure registries setting in /etc/docker/daemon.json in order for this test to pass:
#
#    { "insecure-registries": ["localhost:5000"] }
#
#"
#fi
#echo

cd "$srcdir/docker"
private_key="registry.key"
certificate="registry.crt"
csr="registry.csr"
if ! [ -f "$private_key" -a -f "$certificate" ]; then
    echo "Generating sample SSL certificates:"
    echo
    openssl genrsa -out "$private_key" 2048
    echo
    yes "" | openssl req -new -key "$private_key" -out "$csr" || :
    echo
    openssl x509 -req -days 3650 -in "$csr" -signkey "$private_key" -out "$certificate"
    echo
fi
cd "$srcdir/.."

echo "Bringing up Docker Registry container:"
echo
#docker run -d --name "$name" -p 5000:5000 registry:2
docker-compose up -d
echo

when_ports_available "$max_secs" "$DOCKER_REGISTRY_HOST" "$DOCKER_REGISTRY_PORT"

echo

#export DOCKER_REGISTRY_PORT="$(docker-compose port "docker_${DOCKER_SERVICE}_1" "$DOCKER_REGISTRY_PORT" | sed 's/.*://')"
export DOCKER_REGISTRY_PORT="$(docker port "docker_${DOCKER_SERVICE}_1" "$DOCKER_REGISTRY_PORT" | sed 's/.*://')"

if [ -z "$DOCKER_REGISTRY_PORT" ]; then
    echo "DOCKER_REGISTRY_PORT not found from running container, did container fail to start up properly?"
    exit 1
fi

tag="0.7"
repo1="harisekhon/nagios-plugin-kafka"
repo2="harisekhon/consul:$tag"

echo
for image in $repo1 $repo2; do
    echo "Pulling image $image"
    docker pull "$image"
    echo
    echo "Tagging image $image => $DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT/$image"
    docker tag "$image" "$DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT/$image"
    # cannot specify http:// or https:// - docker will infer the respository from the tag prefix
    echo
    echo "Pushing image $image to Docker Registry $DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT:"
    docker push "$DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT/$image"
    echo
done
echo

export SSL_NOVERIFY=1
check "./docker_registry_show_tags.py -S $repo1 $repo2" "Docker Registry Show Tags for $repo1 & $repo2"
check "./docker_registry_show_tags.py -S ${repo2/:*}" "Docker Registry Show Tags for $repo2"
check "./docker_registry_show_tags.py -S ${repo2/:*} | grep '$tag'" "Docker Registry Show Tags search for $repo2 tag $tag"

#docker rm -f "$name"
#docker-compose down

echo
echo "Docker Registry Show Tags tests passed successfully"
echo
echo

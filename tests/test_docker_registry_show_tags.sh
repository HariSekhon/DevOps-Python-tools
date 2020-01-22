#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-09-12 17:49:29 +0200 (Tue, 12 Sep 2017)
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
srcdir2="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir2/.."

# shellcheck disable=SC1091
. "tests/utils.sh"

# shellcheck disable=SC1091
. "bash-tools/lib/utils.sh"

srcdir="$srcdir2"

section "Testing Docker Registry Show Tags"

check_docker_available

export DOCKER_REGISTRY_HOST="${DOCKER_HOST:-localhost}"
export DOCKER_REGISTRY_HOST="${DOCKER_REGISTRY_HOST/*:\/\/}"
export DOCKER_REGISTRY_HOST="${DOCKER_REGISTRY_HOST/:*}"

export DOCKER_REGISTRY_PORT_DEFAULT=5000

export DOCKER_REGISTRY_USER="${DOCKER_REGISTRY_USER:-docker_user}"
export DOCKER_REGISTRY_PASSWORD="${DOCKER_REGISTRY_PASSWORD:-docker_password}"

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
htpasswd="registry.htpasswd"
csr="registry.csr"
if ! [ -f "$private_key" ] &&
     [ -f "$certificate" ]; then
    echo "Generating sample SSL certificates:"
    echo
    openssl genrsa -out "$private_key" 2048
    echo
    yes "." | openssl req -new -key "$private_key" -out "$csr" || :
    echo
    openssl x509 -req -days 3650 -in "$csr" -signkey "$private_key" -out "$certificate"
    echo
    hr
fi
#if ! [ -f "$htpasswd" ]; then
    echo "generating htpasswd auth file:"
    # -B - becrypt - docker registry ignores entries that don't use very secure Becrypt
    # -b - take password from cli instead of prompting
    # -c - create htpasswd file
    htpasswd -B -b -c "$htpasswd" "$DOCKER_REGISTRY_USER" "$DOCKER_REGISTRY_PASSWORD"
    echo
    hr
#fi
cd "$srcdir/.."

echo "Bringing up Docker Registry container:"
echo
#docker run -d --name "$name" -p 5000:5000 registry:2
docker-compose up -d
hr
echo

echo "getting dynamic Docker Registry port mapping:"
docker_compose_port "Docker Registry"
hr

# shellcheck disable=SC2153
if [ -z "$DOCKER_REGISTRY_PORT" ]; then
    echo "DOCKER_REGISTRY_PORT not found from running container, did container fail to start up properly?"
    exit 1
fi

when_ports_available "$max_secs" "$DOCKER_REGISTRY_HOST" "$DOCKER_REGISTRY_PORT"
hr
when_url_content "$max_secs" "https://$DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT/v2/_catalog" repositories -u "$DOCKER_REGISTRY_USER":"$DOCKER_REGISTRY_PASSWORD"
hr
echo

echo "docker login to registry $DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT ..."
docker login -u "$DOCKER_REGISTRY_USER" -p "$DOCKER_REGISTRY_PASSWORD" "$DOCKER_REGISTRY_HOST:$DOCKER_REGISTRY_PORT"
hr

tag="3.4"
repo1="library/busybox"
repo2="harisekhon/zookeeper:$tag"

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
    hr
    echo
done
hr
echo

export SSL_NOVERIFY=1
check "./docker_registry_show_tags.py -S $repo1 $repo2" "Docker Registry Show Tags for $repo1 & $repo2"
hr
check "./docker_registry_show_tags.py -S ${repo2/:*}" "Docker Registry Show Tags for $repo2"
hr
check "./docker_registry_show_tags.py -S ${repo2/:*} | grep '$tag'" "Docker Registry Show Tags search for $repo2 tag $tag"
hr

#docker rm -f "$name"
docker-compose down

echo
echo "Docker Registry Show Tags tests passed successfully"
echo
echo

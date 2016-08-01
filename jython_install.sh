#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-01 10:17:55 +0100 (Mon, 01 Aug 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -eu
[ -n "${DEBUG:-}" ] && set -x
srcdir="$(cd "$( dirname "$0" )" && pwd)"

JYTHON_VERSION=2.7.0

# not set in busybox
#[ $EUID -eq 0 ] && sudo="" || sudo=sudo
[ $(whoami) = "root" ] && sudo="" || sudo=sudo

if ! [ -e /opt/jython ]; then
    mkdir -p /opt
    wget -cO jython-installer.jar "http://search.maven.org/remotecontent?filepath=org/python/jython-installer/$JYTHON_VERSION/jython-installer-$JYTHON_VERSION.jar"
    $sudo expect "$srcdir/jython_autoinstall.exp"
    $sudo ln -sf "/opt/jython-$JYTHON_VERSION" /opt/jython
    rm -f jython-installer.jar
    echo
    echo "Jython Install done"
else
    echo "/opt/jython already exists - doing nothing"
fi
if ! [ -e /etc/profile.d/jython.sh ]; then
    echo "Adding /etc/profile.d/jython.sh"
    # shell execution tracing comes out in the file otherwise
    set +x
    cat >> /etc/profile.d/jython.sh <<EOF
export JYTHON_HOME=/opt/jython
export PATH=\$PATH:\$JYTHON_HOME/bin
EOF
fi
echo "DONE"

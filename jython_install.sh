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

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "$0}" )" && pwd )"

JYTHON_VERSION=2.7.0

if ! [ -e /opt/jython ]; then
    mkdir -p /opt
    wget -cO jython-installer.jar "http://search.maven.org/remotecontent?filepath=org/python/jython-installer/$JYTHON_VERSION/jython-installer-$JYTHON_VERSION.jar"
    "$srcdir/jython_autoinstall.exp"
    ln -sf "/opt/jython-$JYTHON_VERSION" /opt/jython
    rm -f jython-installer.jar
    echo "Jython Install DONE - Add /opt/jython/bin to your \$PATH"
else
    echo "/opt/jython already exists - doing nothing"
fi

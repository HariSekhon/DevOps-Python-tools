#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-29 18:18:39 +0100 (Mon, 29 Aug 2016)
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
srcdir="$(cd "$(dirname "$0")" && pwd)"

cd "$srcdir";

# shellcheck disable=SC1091
. utils.sh

# shellcheck disable=SC1091
. ../bash-tools/lib/utils.sh

section "JSON => XML"

#tmpfile="$(mktemp json_to_xml_test.XXXXX.xml)"
#echo "tmpfile is $tmpfile"

#trap "rm -f $tmpfile" $TRAP_SIGNALS

echo "running json_to_xml.py:"
../json_to_xml.py data/test.json | tee /dev/stderr | validate_xml.py
echo

echo "running json_to_xml.py from stdin:"
../json_to_xml.py < data/test.json | tee /dev/stderr | validate_xml.py
echo

echo "JSON to XML tests succeeded!"
echo

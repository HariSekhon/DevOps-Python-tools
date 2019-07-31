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

. utils.sh
. ../bash-tools/lib/utils.sh

section "XML => JSON"

for x in simple.xml plant_catalog.xml; do
    tmpfile="$(mktemp xml_to_json_test.XXXXX.xml)"
    trap "rm -f $tmpfile" $TRAP_SIGNALS
    echo "running xml_to_json.py on $x":
    ../xml_to_json.py "data/$x" > "$tmpfile"
    echo
    echo "now validating generated json":
    ../validate_json.py "$tmpfile"
    echo
    rm -f "$tmpfile"
    echo "========="
done

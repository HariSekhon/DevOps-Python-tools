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

section "XML => YAML"

cd ..

testdata="tests/data/simple.xml"

echo "running xml_to_yaml.py on $testdata":
./xml_to_yaml.py "$testdata" | tee /dev/stderr | ./validate_yaml.py
echo

echo "running xml_to_yaml.py on stdin < $testdata":
./xml_to_yaml.py < "$testdata" | tee /dev/stderr | ./validate_yaml.py
echo

echo "running xml_to_yaml.py on tests/data/plant_catalog.xml":
./xml_to_yaml.py "tests/data/plant_catalog.xml" | ./validate_yaml.py
echo
echo "XML to yaml tests succeeded!"
echo

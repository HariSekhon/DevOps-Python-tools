#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-12-19 18:04:15 +0000 (Thu, 19 Dec 2019)
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

section "JSON => YAML"

cd ..

tmpfile="$(mktemp json_to_yaml_test.XXXXX.yml)"
#echo "tmpfile is $tmpfile"

# want var splitting
# shellcheck disable=SC2086
trap 'rm -f "$tmpfile"' $TRAP_SIGNALS

for x in ./cloudformation/centos7-12nodes-encrypted.json tests/data/embedded_double_quotes.json; do
    echo "running json_to_yaml.py $x"
    ./json_to_yaml.py "$x" > "$tmpfile"
    echo "now validating generated yaml"
    ./validate_yaml.py "$tmpfile"
    echo
done

echo "recursing directory to convert all json files under a directory tree to yaml"
./json_to_yaml.py cloudformation/ > "$tmpfile"
# TODO: fix validate_yaml.py to work on multi-yamls with --- and re-enable
#echo "now validating generated yaml"
#./validate_yaml.py "$tmpfile"
echo "Success"

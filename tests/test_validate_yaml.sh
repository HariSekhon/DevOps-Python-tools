#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-12-22 23:39:33 +0000 (Tue, 22 Dec 2015)
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
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

section "Testing validate_yaml.py"

export TIMEOUT=5
if is_inside_docker; then
    export TIMEOUT=10
fi

if [ $# -gt 0 ]; then
    echo "validate_yaml.py $*"
    ./validate_yaml.py "$@"
    echo
fi

data_dir="tests/data"
broken_dir="tests/yaml_broken"

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

./validate_yaml.py --exclude "$exclude" .
echo

echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_yaml.py "$data_dir/test.yaml" .
echo

echo "checking symlink handling"
ln -sfv "test.yaml" "$data_dir/testlink.yaml"
./validate_yaml.py "$data_dir/testlink.yaml"
rm "$data_dir/testlink.yaml"
echo

echo "checking yaml file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.yaml' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_yaml.py -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_yaml.py - < "$data_dir/test.yaml"
./validate_yaml.py < "$data_dir/test.yaml"
echo "testing stdin mixed with filename"
# shellcheck disable=SC2094
./validate_yaml.py "$data_dir/test.yaml" - < "$data_dir/test.yaml"
echo

echo "testing print mode"
[ "$(./validate_yaml.py -p "$data_dir/test.yaml" | cksum)" = "$(cksum < "$data_dir/test.yaml")" ] || { echo "print test failed!"; exit 1; }
echo "successfully passed out test yaml to stdout"
echo

echo "Now trying non-yaml files to detect successful failure:"
check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_yaml.py -t 1 $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
        echo "successfully detected broken yaml in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken yaml in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken yaml in '$filename'"
        exit 1
    fi
}
cat > "$broken_dir/broken_tabs.yaml" <<EOF
---
name:   Hari Sekhon
    age:    21
EOF

check_broken "$broken_dir/broken_tabs.yaml"

cat "$data_dir/test.yaml" >> "$broken_dir/multi-broken.yaml"
cat "$data_dir/test.yaml" >> "$broken_dir/multi-broken.yaml"

check_broken "$broken_dir/multi-broken.yaml"

# csv, ini, json and ldif all pass Python's yaml parser
check_broken_sample_files yaml csv ini json ldif

check_broken README.md

rm -fr "$broken_dir"

echo

echo "checking for non-existent file"
check_broken nonexistentfile 2
echo

rm -fv "$data_dir/test.yml"

echo "======="
echo "SUCCESS"
echo "======="

echo
echo

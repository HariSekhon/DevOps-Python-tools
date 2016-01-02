#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-12-22 23:39:33 +0000 (Tue, 22 Dec 2015)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

set -euo pipefail
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "
# ======================== #
# Testing validate_yaml.py
# ======================== #
"

cd "$srcdir/..";

. ./tests/utils.sh

until [ $# -lt 1 ]; do
    case $1 in
        -*) shift
    esac
done

data_dir="tests/data"
broken_dir="tests/yaml_broken"

rm -fr "$broken_dir" || :
mkdir "$broken_dir"
./validate_yaml.py -vvv $(
find "${1:-.}" -iname '*.yaml' |
grep -v '/spark-.*-bin-hadoop.*/' |
grep -v -e 'broken' -e 'error' -e ' '
) "$data_dir/test.json" # json is an official subset, "inline-style"
echo

echo "checking yaml file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.yaml' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_yaml.py -vvv -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_yaml.py - < "$data_dir/test.yaml"
./validate_yaml.py < "$data_dir/test.yaml"
echo "testing stdin mixed with filename"
./validate_yaml.py "$data_dir/test.yaml" - < "$data_dir/test.yaml"
echo

echo "Now trying non-yaml files to detect successful failure:"
check_broken(){
    filename="$1"
    set +e
    ./validate_yaml.py -vvv -t 1 "$filename" ${@:2}
    result=$?
    set -e
    if [ $result = 2 ]; then
        echo "successfully detected broken yaml in '$filename', returned exit code $result"
        echo
    #elif [ $result != 0 ]; then
    #    echo "returned unexpected non-zero exit code $result for broken yaml in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $result for broken yaml in '$filename'"
        exit 1
    fi
}
check_broken "$data_dir/multirecord.json"
check_broken "$data_dir/test_broken_tabs.yaml"
check_broken README.md
cat "$data_dir/test.yaml" >> "$broken_dir/multi-broken.yaml"
cat "$data_dir/test.yaml" >> "$broken_dir/multi-broken.yaml"
check_broken "$broken_dir/multi-broken.yaml"
rm -fr "$broken_dir"
echo "======="
echo "SUCCESS"
echo "======="

echo
echo

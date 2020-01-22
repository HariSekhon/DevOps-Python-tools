#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-08-20 12:56:43 +0100 (Sun, 20 Aug 2017)
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
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

section "Testing validate_ldap_ldif.py"

if [ $# -gt 0 ]; then
    echo "validate_ldap_ldif.py $*"
    ./validate_ldap_ldif.py "$@"
    echo
fi

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

data_dir="tests/data"
broken_dir="tests/broken_ldif"

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

export TIMEOUT=5

./validate_ldap_ldif.py --exclude "$exclude" .
echo

echo "checking directory recursion (mixed with explicit file given)"
./validate_ldap_ldif.py "$data_dir/add_ou.ldif" .
echo

echo "checking symlink handling"
ln -sfv "add_ou.ldif" "$data_dir/testlink.ldif"
./validate_ldap_ldif.py "$data_dir/testlink.ldif"
rm "$data_dir/testlink.ldif"
echo

echo "checking ldif file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.ldif' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_ldap_ldif.py "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_ldap_ldif.py - < "$data_dir/add_ou.ldif"
./validate_ldap_ldif.py < "$data_dir/add_ou.ldif"
# shellcheck disable=SC2094
./validate_ldap_ldif.py "$data_dir/add_ou.ldif" - < "$data_dir/add_ou.ldif"
echo

echo "testing multiple entry ldif"
cat "$data_dir/add_ou.ldif" >> "$broken_dir/multi-broken.ldif"
cat "$data_dir/add_ou.ldif" >> "$broken_dir/multi-broken.ldif"
./validate_ldap_ldif.py "$broken_dir/multi-broken.ldif"
echo

echo "testing print mode"
[ "$(./validate_ldap_ldif.py -p "$data_dir/add_ou.ldif" | cksum)" = "$(cksum < "$data_dir/add_ou.ldif")" ] || { echo "print test failed!"; exit 1; }
echo "successfully passed out test ldif to stdout"
echo

echo "testing stdin print mode"
[ "$(./validate_ldap_ldif.py -p - < "$data_dir/add_ou.ldif" | cksum)" = "$(cksum < "$data_dir/add_ou.ldif")" ] || { echo "print stdin test failed!"; exit 1; }
echo "successfully passed out stdin test ldif to stdout"
echo

check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_ldap_ldif.py $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
        echo "successfully detected broken ldif in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken ldif in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken ldif in '$filename'"
        exit 1
    fi
}

echo > "$broken_dir/blank.ldif"
check_broken "$broken_dir/blank.ldif"
# break by replacing dn field
sed 's/^dn:/replaceddn:/' "$data_dir/add_ou.ldif" > "$broken_dir/missing_dn.ldif"
check_broken "$broken_dir/missing_dn.ldif"
{ echo "notdnfirst: test"; sed 's/#.*//' "$data_dir/add_ou.ldif"; } > "$broken_dir/first_entry_not_dn.ldif"
check_broken "$broken_dir/first_entry_not_dn.ldif"

check_broken_sample_files ldif

echo "checking for non-existent file"
check_broken nonexistentfile 2
echo

rm -fr "$broken_dir"

echo "======="
echo "SUCCESS"
echo "======="

echo
echo

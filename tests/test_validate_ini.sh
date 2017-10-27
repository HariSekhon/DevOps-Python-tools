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
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

. ./tests/utils.sh

section "Testing validate_ini.py"

export TIMEOUT=3

if [ $# -gt 0 ]; then
    echo "validate_ini.py $@"
    ./validate_ini.py $@
    echo
fi

data_dir="tests/data"
broken_dir="tests/ini_broken"

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

./validate_ini.py --exclude "$exclude" .
echo


# ==================================================
hr2
echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_ini.py "$data_dir/test.ini" "$data_dir"
echo

# ==================================================
hr2
echo "checking symlink handling"
ln -sfv "test.ini" "$data_dir/testlink.ini"
./validate_ini.py "$data_dir/testlink.ini"
rm "$data_dir/testlink.ini"
echo

# ==================================================
hr2
echo "checking ini file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.ini' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_ini.py -t 1 "$broken_dir/no_extension_testfile"
echo

# ==================================================
hr2
echo "testing stdin"
./validate_ini.py - < "$data_dir/test.ini"
./validate_ini.py < "$data_dir/test.ini"
echo "testing stdin mixed with filename"
./validate_ini.py "$data_dir/test.ini" - < "$data_dir/test.ini"
echo

echo "testing print mode"
if [ "$(./validate_ini.py -p "$data_dir/test.ini" | cksum)" != "$(cksum < "$data_dir/test.ini")" ]; then
    echo "print test failed! "
    exit 1
fi
echo "successfully passed out test ini to stdout"
echo

# ==================================================
hr2
check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${@:3}"
    set +e
    ./validate_ini.py -t 1 $options "$filename"
    exitcode=$?
    set -e
    if [ $exitcode = $expected_exitcode ]; then
        echo "successfully detected broken ini in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken ini in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken ini in '$filename'"
        exit 1
    fi
}

hr2
echo "checking ini with blanks fails with --no-blank-lines:"
check_broken test.ini 2 --no-blank-lines
echo

hr2
echo "checking ini with colons fails:"
check_broken "$data_dir/test.ini-colons"
echo

hr2
echo "checking ini with colons passes with --allow-colon-delimiters:"
./validate_ini.py --allow-colon-delimiters "$data_dir/test.ini-colons"
echo

hr2
echo "checking ini with hashes comments passes:"
./validate_ini.py "$data_dir/test.ini-hashes"
echo

hr2
echo "checking ini with hash comments fails with --no-hash-comments:"
check_broken "$data_dir/test.ini-hashes" 2 --no-hash-comments
echo

hr2
echo "checking ini just bracket fails"
cat "$data_dir/test.ini" > "$broken_dir/test_bracket.ini"
echo "[" >> "$broken_dir/test_bracket.ini"
check_broken "$broken_dir/test_bracket.ini"
echo
hr2

echo
echo "Now testing ini duplicate key and sections detection:"
echo

hr2
echo "checking ini with global single property passes:"
echo "key1=value1" > "$broken_dir/duplicate_properties_global.ini"
./validate_ini.py "$broken_dir/duplicate_properties_global.ini"

echo "checking ini global duplicate property fails:"
echo "key1=value1" >> "$broken_dir/duplicate_properties_global.ini"
check_broken "$broken_dir/duplicate_properties_global.ini"

hr2
echo "checking ini sections with non-duplicate properties passes:"
echo "[section1]
key2=value2
key3=value3
[section2]
key2=value2
key3=value3
" > "$broken_dir/duplicate_properties_section.ini"

./validate_ini.py "$broken_dir/duplicate_properties_section.ini"

echo "checking ini section with duplicate properties fails:"
echo "key3=value3" >> "$broken_dir/duplicate_properties_section.ini"
check_broken "$broken_dir/duplicate_properties_section.ini"

hr2
echo "checking ini with non-duplicate sections passes:"
echo "[section1]
key4=value4
key5=value5

[section2]
key6=value6
key7=value7
" > "$broken_dir/duplicate_sections.ini"
./validate_ini.py "$broken_dir/duplicate_sections.ini"

hr
echo "checking ini with duplicate sections fails:"
echo "
[section2]
key8=value8
key9=value9" >> "$broken_dir/duplicate_sections.ini"
check_broken "$broken_dir/duplicate_sections.ini"

echo

hr2
check_broken_sample_files ini

# ==================================================
hr2
echo "checking single word text file is not valid ini"
echo blah > "$broken_dir/single_field.ini"
check_broken "$broken_dir/single_field.ini" 2

# ==================================================
hr2
echo "checking for non-existent file"
check_broken nonexistentfile 2

# ==================================================
hr2
echo "checking blank content is invalid"
echo > "$broken_dir/blank.ini"
check_broken "$broken_dir/blank.ini"
echo

hr2
echo "checking blank content is invalid via stdin"
check_broken - 2 < "$broken_dir/blank.ini"
echo

hr2
echo "checking blank content is invalid via stdin piped from /dev/null"
cat /dev/null | check_broken - 2
echo

hr2
echo "checking commented out ini is invalid due to no keys or sections:"
cat >> "$broken_dir/commented_out.ini" <<EOF
#[section1]
#key1=value1

EOF
check_broken "$broken_dir/commented_out.ini"
echo
hr2
echo "checking commented out ini is permitted if using --allow-empty:"
./validate_ini.py --allow-empty "$broken_dir/commented_out.ini"
echo

hr2
echo "checking commented out ini is permitted if using --allow-empty via std:"
./validate_ini.py --allow-empty < "$broken_dir/commented_out.ini"
echo

hr2
echo "checking blank ini is permitted if using --allow-empty:"
validate_ini.py --allow-empty "$broken_dir/blank.ini"
echo

hr2
echo "checking blank ini is permitted if using --allow-empty via stdin:"
validate_ini.py --allow-empty < "$broken_dir/blank.ini"
echo

hr2
echo "checking blank ini is permitted if using --allow-empty via stdin piped from /dev/null:"
validate_ini.py --allow-empty < /dev/null
echo

rm -fr "$broken_dir"

echo "======="
echo "SUCCESS"
echo "======="

echo
echo

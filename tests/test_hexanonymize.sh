#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-01-02 17:35:08 +0000 (Thu, 02 Jan 2020)
#
#  https://github.com/harisekhon/devop-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#

set -eu
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

section "HexAnonymize"

start_time=$(date +%s)

run++
check_output "abc123456def789012abcd" hexanonymize.py <<< "xyz987654rst654321AKIA"

run++
check_output "abc123456def789012ABCD" hexanonymize.py -c <<< "xyz987654rst654321AKIA"

run++
check_output "xyz123456rst789012abC" hexanonymize.py -c -o <<< "xyz987654rst654321caD"

run++
check_output "xyz123456rst789012abc" hexanonymize.py -o <<< "xyz987654rst654321caD"

echo
# $run_count defined in lib
# shellcheck disable=SC2154
echo "Total Tests run: $run_count"
time_taken "$start_time" "All version tests for hexanonymize.py completed in"
echo
untrap

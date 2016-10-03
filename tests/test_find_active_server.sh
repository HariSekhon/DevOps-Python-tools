#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-03 11:44:41 +0100 (Mon, 03 Oct 2016)
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

srcdir="$(cd "$(dirname "$0")" && pwd)"

cd "$srcdir/.."

. bash-tools/utils.sh

set +e +o pipefail

section "find_active_server.py"

#datestring="$(date '+%F')"

unset HOST

echo "testing socket ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py yahoo.com google.com --port 80

check_output "google.com" ./find_active_server.py 0.0.0.0 google.com yahoo.com --port 80

hr
echo "testing socket ordering result consistency with individual port overrides"
echo

check_output "yahoo.com:80" ./find_active_server.py yahoo.com:80 google.com --port 1

check_output "google.com:80" ./find_active_server.py yahoo.com google.com:80 --port 1

# ============================================================================ #
hr
echo "checking --port --ping switch conflict fails"
echo
./find_active_server.py 0.0.0.0 google.com --port 1 --ping
check_exit_code 3
echo
hr

echo "testing ping ordering result consistency"
echo
check_output "google.com" ./find_active_server.py 0.0.0.0 google.com --ping

hr
echo "testing ping ordering result consistency with individual port overrides"
echo

check_output "google.com" ./find_active_server.py 0.0.0.0 google.com:80 --ping

# ============================================================================ #
hr
echo
echo "testing http ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py yahoo.com google.com --http

check_output "google.com" ./find_active_server.py 0.0.0.0 google.com yahoo.com --http

hr
echo
echo "testing https ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py yahoo.com google.com --https

check_output "google.com" ./find_active_server.py 0.0.0.0 google.com yahoo.com --https

echo
echo "testing https returns no results when using wrong port 25"
echo

check_output "" ./find_active_server.py mail.google.com --https --port 25

# ============================================================================ #
hr
echo
echo "testing HTTP regex filtering excludes first result"
echo

check_output "yahoo.com" ./find_active_server.py yahoo.com google.com --http --regex 'yahoo.*'

check_output "yahoo.com" ./find_active_server.py google.com yahoo.com --http --regex 'yahoo.*'

# ============================================================================ #
hr
echo
echo "testing HTTPS regex filtering excludes first result"
echo

check_output "yahoo.com" ./find_active_server.py yahoo.com google.com --https --regex 'yahoo.*'

check_output "yahoo.com" ./find_active_server.py google.com yahoo.com --https --regex 'yahoo.*'

# ============================================================================ #
hr
echo
echo "testing random socket result selection"
echo

#output="$(./find_active_server.py google.com google.co.uk --random --port 80 2>&1)"
#[[ "$output" = *google* ]] || die "FAILED: --random google socket test"
check_output "*google*" ./find_active_server.py google.com google.co.uk --random --port 80

# ============================================================================ #
hr
echo
echo "testing random socket select 10 times contains both google and yahoo results"
echo

output="$(for x in {1..10}; do ./find_active_server.py google.com yahoo.com --random --port 80 2>&1; done)"
grep "google.com" <<< "$output" &&
grep "yahoo.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return both results for 10 random runs"
echo

# ============================================================================ #
hr
echo
echo "testing random http result selection"
echo

check_output "*google*" ./find_active_server.py google.com google.co.uk --random --http

# ============================================================================ #
hr
echo
echo "testing random https result selection"
echo

check_output "*google*" ./find_active_server.py google.com google.co.uk --random --https

# ============================================================================ #
hr
echo
echo "testing random http select 10 times contains both google and yahoo results"
echo

output="$(for x in {1..10}; do ./find_active_server.py google.com yahoo.com --random --http 2>&1; done)"
grep "google.com" <<< "$output" &&
grep "yahoo.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return both results for 10 random HTTP runs"
echo

# ============================================================================ #
hr
echo
echo "testing random https select 10 times contains both google and yahoo results"
echo

output="$(for x in {1..10}; do ./find_active_server.py google.com yahoo.com --random --https 2>&1; done)"
grep "google.com" <<< "$output" &&
grep "yahoo.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return both results for 10 random HTTP runs"
echo

# ============================================================================ #
hr
echo
echo "testing random result selection with regex returns google but omits yahoo"
echo

output="$(for x in {1..10}; do ./find_active_server.py google.com yahoo.com --random --https --regex yahoo 2>&1; done)"
grep "yahoo.com" <<< "$output" &&
! grep "google.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return only google results for 10 random HTTP runs with regex filter"

echo
echo "SUCCEEDED - all tests passed for find_active_server.py"

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

check_output "yahoo.com" ./find_active_server.py yahoo.com google.com --port 80 -n1

check_output "google.com" ./find_active_server.py 0.0.0.1 google.com yahoo.com --port 80 -n1

hr
echo "testing socket ordering result consistency with individual port overrides"
echo

check_output "yahoo.com:80" ./find_active_server.py yahoo.com:80 google.com --port 1 -n1

check_output "google.com:80" ./find_active_server.py yahoo.com google.com:80 --port 1 -n1

# ============================================================================ #
hr
echo "checking --port --ping switch conflict fails"
echo
./find_active_server.py 0.0.0.1 google.com --port 1 --ping -n1
check_exit_code 3
echo

hr
echo "checking --ping and --http switch conflict fails"
echo
./find_active_server.py 0.0.0.1 google.com --ping --http
check_exit_code 3
echo

# ============================================================================ #
hr
echo "testing ping ordering result consistency"
echo
check_output "google.com" ./find_active_server.py 0.0.0.1 google.com --ping -n1

hr
echo "testing ping ordering result consistency with individual port overrides"
echo

check_output "google.com" ./find_active_server.py 0.0.0.1 google.com:80 --ping -n1

# ============================================================================ #
hr
echo "testing http ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py 0.0.0.1 yahoo.com google.com --http -n1

check_output "google.com" ./find_active_server.py google.com yahoo.com --http -n1

hr
echo "testing https ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py yahoo.com google.com --https -n1

check_output "google.com" ./find_active_server.py 0.0.0.1 google.com yahoo.com --https -n1

echo
echo "testing https returns no results when using wrong port 25"
echo

check_output "" ./find_active_server.py mail.google.com --https --port 25

echo
echo "testing https with url suffix and regex matching"
echo

check_output "github.com" ./find_active_server.py --https google.com github.com -u /harisekhon --regex 'pytools'

# ============================================================================ #
hr
echo "testing HTTP regex filtering"
echo

check_output "yahoo.com" ./find_active_server.py google.com yahoo.com --http --regex 'yahoo'

# ============================================================================ #
hr
echo "testing HTTPS regex filtering"
echo

check_output "yahoo.com" ./find_active_server.py google.com yahoo.com --https --regex '(?:yahoo)'

# ============================================================================ #
hr
echo "testing random socket select 10 times contains both google and yahoo results"
echo

output="$(for x in {1..10}; do ./find_active_server.py google.com yahoo.com --random -n1 --port 80 2>&1; done)"
grep "google.com" <<< "$output" &&
grep "yahoo.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return both results for 10 random runs"
echo

# ============================================================================ #
hr
echo "testing random http select 10 times contains both google and yahoo results"
echo

output="$(for x in {1..10}; do ./find_active_server.py google.com yahoo.com --http --random -n1 2>&1; done)"
grep "google.com" <<< "$output" &&
grep "yahoo.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return both results for 10 random HTTP runs"
echo

echo
echo "SUCCEEDED - all tests passed for find_active_server.py"

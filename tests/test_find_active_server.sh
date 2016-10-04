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

# this is set to localhost in Travis CI, which via --host takes precedence and messes with our expected first result
unset HOST

# not using nonexistent DNS servers as some environments have DNS servers which respond with a generic catch all address
# which will mess with results, hence using IP addresses

# can't use this, accidentally succeeds in Travis CI:
# 0.0.0.0 ping => 127.0.0.1

# test both types of unsuitable hosts:
#
# 0.0.0.1 ping => connect: Invalid argument
# 4.4.4.4 ping => no response

opts="-v"

# Travis CI seems to fail to find things online when they clearly are available, perhaps it's the network delay, increasing
# per request timeout to try to make this more tolerant
if is_CI; then
    opts="$opts --request-timeout 5 --timeout 30"
fi

echo "testing socket ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py $opts --num-threads 1 --port 80 yahoo.com google.com

check_output "google.com" ./find_active_server.py $opts --num-threads 1 --port 80 0.0.0.1 4.4.4.4 google.com yahoo.com

hr
echo "testing socket ordering result consistency with individual port overrides"
echo

check_output "yahoo.com:80" ./find_active_server.py $opts -n1 yahoo.com:80 google.com --port 1

check_output "google.com:80" ./find_active_server.py $opts -n1 yahoo.com google.com:80 --port 1

# ============================================================================ #
hr
echo "checking --ping and --port switch conflict fails"
echo
./find_active_server.py $opts -n1 0.0.0.1 4.4.4.4 google.com --ping --port 1
check_exit_code 3
echo

hr
echo "checking --ping and --http switch conflict fails"
echo
./find_active_server.py $opts -n1 0.0.0.1 4.4.4.4 google.com --ping --http
check_exit_code 3
echo

# ============================================================================ #
hr
echo "testing ping ordering result consistency"
echo
check_output "google.com" ./find_active_server.py $opts -n1 0.0.0.1 4.4.4.4 google.com --ping

hr
echo "testing ping ordering result consistency with individual port overrides"
echo

check_output "google.com" ./find_active_server.py $opts -n1 0.0.0.1 4.4.4.4 google.com:80 --ping

# ============================================================================ #
hr
echo "testing http ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py $opts -n1 0.0.0.1 4.4.4.4 yahoo.com google.com --http

check_output "google.com" ./find_active_server.py $opts -n1 google.com yahoo.com --http

hr
echo "testing https ordering result consistency"
echo

check_output "yahoo.com" ./find_active_server.py $opts -n1 yahoo.com google.com --https

check_output "google.com" ./find_active_server.py $opts -n1 0.0.0.1 4.4.4.4 google.com yahoo.com --https

echo
echo "testing https returns no results when using wrong port 25"
echo

# DEBUG=1 breaks this to return NO_AVAILABLE_SERVER
#check_output "" ./find_active_server.py $opts mail.google.com --https --port 25

check_output "NO_AVAILABLE_SERVER" ./find_active_server.py $opts mail.google.com --https --port 25

echo
echo "testing https with url suffix and regex matching"
echo

check_output "github.com" ./find_active_server.py $opts --https google.com github.com -u /harisekhon --regex 'pytools'

# ============================================================================ #
hr
echo "testing HTTP regex filtering"
echo

check_output "yahoo.com" ./find_active_server.py $opts google.com yahoo.com --http --regex 'yahoo'

# ============================================================================ #
hr
echo "testing HTTPS regex filtering"
echo

check_output "yahoo.com" ./find_active_server.py $opts google.com yahoo.com --https --regex '(?:yahoo)'

# ============================================================================ #
hr
echo "testing random socket select 10 times contains both google and yahoo results"
echo

output="$(for x in {1..10}; do ./find_active_server.py -n1 google.com yahoo.com --random --port 80 2>&1; done)"
grep "google.com" <<< "$output" &&
grep "yahoo.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return both results for 10 random runs"
echo

# ============================================================================ #
hr
echo "testing random http select 10 times contains both google and yahoo results"
echo

output="$(for x in {1..10}; do ./find_active_server.py -n1 google.com yahoo.com --http --random 2>&1; done)"
grep "google.com" <<< "$output" &&
grep "yahoo.com" <<< "$output" ||
    die "FAILED: --random google + yahoo test, didn't return both results for 10 random HTTP runs"
echo

echo
echo "SUCCEEDED - all tests passed for find_active_server.py"

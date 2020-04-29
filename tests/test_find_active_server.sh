#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-03 11:44:41 +0100 (Mon, 03 Oct 2016)
#
#  https://github.com/harisekhon/python-tools
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

# shellcheck disable=SC1091
. bash-tools/lib/utils.sh

set +e +o pipefail

section "find_active_server.py"

start_time="$(start_timer "find_active_server.py test")"

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

# sometimes Yahoo http is a bit slow
export REQUEST_TIMEOUT=5
export TIMEOUT=20

SITE1="duckduckgo"
SITE2="google"

# put the faster website second
WEBSITE1="duckduckgo.com"
WEBSITE2="google.com"

opts="-v"

# Travis CI seems to fail to find things online when they clearly are available, perhaps it's the network delay, increasing
# per request timeout to try to make this more tolerant
if is_CI; then
    # too much output, causes Travis CI to fail job
    unset DEBUG
    export VERBOSE=0
    #opts="$opts -v --request-timeout 10 --timeout 30"
    # these options are all supported via environment now
    export REQUEST_TIMEOUT=10
    export TIMEOUT=30
fi

echo "testing socket ordering result consistency:"
echo

run_grep "^$WEBSITE1$" ./find_active_server.py $opts --num-threads 1 --port 80 $WEBSITE1 $WEBSITE2

echo "testing socket returns only functional server:"
echo

run_grep "^$WEBSITE2$" ./find_active_server.py $opts --port 80 0.0.0.1 $WEBSITE2

echo "testing socket ordering result consistency with individual port overrides:"
echo

run_grep "^$WEBSITE1:80$" ./find_active_server.py $opts --port 1 $WEBSITE1:80 $WEBSITE2

run_grep "^$WEBSITE1:80$" ./find_active_server.py $opts --port 1 $WEBSITE2 $WEBSITE1:80

# ============================================================================ #

echo "checking --ping and --port switch conflict fails:"
echo
run_fail 3 ./find_active_server.py $opts --ping --port 1 $WEBSITE1 $WEBSITE2

echo "checking --ping and --http switch conflict fails:"
echo
run_fail 3 ./find_active_server.py $opts --ping --http $WEBSITE1 $WEBSITE2

# ============================================================================ #

echo "testing ping returns only functional server:"
echo
run_grep "^$WEBSITE2$" ./find_active_server.py $opts --ping 0.0.0.1 4.4.4.4 $WEBSITE2

echo "testing ping returns only functional server, ignoring port override:"
echo

run_grep "^$WEBSITE2$" ./find_active_server.py $opts -n1 --ping 0.0.0.1 4.4.4.4 $WEBSITE2:80

# ============================================================================ #

echo "testing http ordering result consistency:"
echo

# Google's server latency is so much less than yahoo's that giving -n2 will allow $WEBSITE2 to overtake $WEBSITE1, limit to 1 so that yahoo gets the next available slot
run_grep "^$WEBSITE1$" ./find_active_server.py $opts -n1 --http 0.0.0.1 $WEBSITE1 $WEBSITE2

echo "testing https ordering result consistency:"
echo

run_grep "^$WEBSITE1$" ./find_active_server.py $opts -n1 --https $WEBSITE1 $WEBSITE2

# there is an bug somewhere in Alpine Linux's libraries where only --https doesn't limit concurrency and the yahoo result is often faster on https, breaking this test
# works fine on normal Linux distributions like Centos, Debian and Ubuntu
run_grep "^$WEBSITE2$" ./find_active_server.py $opts -n1 --https 0.0.0.1 $WEBSITE2 $WEBSITE1

echo "testing blank result for localhost 9999:"
echo
DEBUG="" ERRCODE=1 run_grep "^$" ./find_active_server.py --https localhost --port 9999 -q

echo "testing NO_AVAILABLE_SERVER for localhost 9999 verbose:"
echo
ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_server.py --https localhost --port 9999

#echo
#echo "testing http returns no results when using wrong port 25"
#echo

# DEBUG=1 breaks this to return NO_AVAILABLE_SERVER
#DEBUG="" ERRCODE=1 run_grep "^$" ./find_active_server.py $opts mail.$WEBSITE2 --http --port 25

# hangs a bit
#ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_server.py $opts mail.$WEBSITE2 --https --port 25

echo "testing https with url path and regex matching:"
echo

run_grep "^github.com$" ./find_active_server.py $opts --https $WEBSITE2 github.com -u /harisekhon --regex '(?i)python-tools'

# ============================================================================ #

echo "testing HTTP regex filtering:"
echo

run_grep "^$WEBSITE1$" ./find_active_server.py $opts --http --regex "$SITE1" $WEBSITE2 $WEBSITE1

# ============================================================================ #

echo "testing HTTPS regex filtering:"
echo

run_grep "^$WEBSITE1$" ./find_active_server.py $opts --https --regex "(?:$SITE1)" $WEBSITE2 $WEBSITE1

# ============================================================================ #

echo "testing random socket select 10 times contains both $SITE1 and $SITE2 results:"
echo

# Google's servers are consistenly so much faster / lower latency that I end up with all 10 as google here, must restrict to single threaded random to allow yahoo to succeed
#output="$(for x in {1..10}; do ./find_active_server.py -n1 --random --port 80 $WEBSITE2 $WEBSITE1; done)"
#grep "$WEBSITE2" <<< "$output" &&
#grep "$WEBSITE1" <<< "$output" ||
#    die "FAILED: --random google + yahoo test, didn't return both results for 10 random runs"
# more efficient - stop as soon as both results are returned, typically 2-3 runs rather than 10 runs
count_socket_attempts=0
found_google_socket=0
found_duckduckgo_socket=0
run++
for _ in {1..10}; do
    echo -n .
    ((count_socket_attempts+=1))
    output="$(./find_active_server.py -n1 --random --port 80 $WEBSITE1 $WEBSITE2)"
    if [ "$output" = "$WEBSITE2" ]; then
        found_google_socket=1
    elif [ "$output" = "$WEBSITE1" ]; then
        found_duckduckgo_socket=1
    fi
    [ $found_google_socket -eq 1 ] && [ $found_duckduckgo_socket -eq 1 ] && break
done
echo
if [ $found_google_socket -eq 1 ] && [ $found_duckduckgo_socket -eq 1 ]; then
    echo "Found both $WEBSITE1 and $WEBSITE2 in results from $count_socket_attempts --random runs"
else
    die "Failed to return both $WEBSITE1 and $WEBSITE2 in results from $count_socket_attempts --random runs"
fi
echo
hr

# ============================================================================ #

echo "testing random http select 10 times contains both $SITE1 and $SITE2 results:"
echo

#output="$(for x in {1..10}; do ./find_active_server.py -n1 --http --random $WEBSITE2 $WEBSITE1; done)"
#grep "$WEBSITE2" <<< "$output" &&
#grep "$WEBSITE1" <<< "$output" ||
#    die "FAILED: --random google + duckduckgo test, didn't return both results for 10 random HTTP runs"
#echo
#
# more efficient - stop as soon as both results are returned, typically 2-3 runs rather than 10 runs
count_http_attempts=0
found_google_http=0
found_duckduckgo_http=0
run++
for _ in {1..10}; do
    echo -n .
    ((count_http_attempts+=1))
    output="$(./find_active_server.py -n1 --http --random $WEBSITE1 $WEBSITE2)"
    if [ "$output" = "$WEBSITE2" ]; then
        found_google_http=1
    elif [ "$output" = "$WEBSITE1" ]; then
        found_duckduckgo_http=1
    fi
    [ $found_google_http -eq 1 ] && [ $found_duckduckgo_http -eq 1 ] && break
done
echo
if [ $found_google_http -eq 1 ] && [ $found_duckduckgo_http -eq 1 ]; then
    echo "Found both $WEBSITE1 and $WEBSITE2 in results from $count_http_attempts --random runs"
else
    die "Failed to return both $WEBSITE1 and $WEBSITE2 in results from $count_http_attempts --random runs"
fi
hr
echo
# $run_count defined in lib
# shellcheck disable=SC2154
echo "Tests run: $run_count"
time_taken "$start_time" "find_active_server.py tests completed in"
echo

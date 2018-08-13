#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-07-28 18:47:41 +0100 (Tue, 28 Jul 2015)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

test_num="${1:-}"
parallel=""
if [ "$test_num" = "p" ]; then
    parallel="1"
    test_num=""
fi

cd "$srcdir/..";

. ./tests/utils.sh

src[0]="2015-11-19 09:59:59,893 - Execution of 'mysql -u root --password=somep@ssword! -h myHost.internal  -s -e \"select version();\"' returned 1. ERROR 2003 (HY000): Can't connect to MySQL server on 'host.domain.com' (111)"
dest[0]="2015-11-19 09:59:59,893 - Execution of 'mysql -u root --password=<password> -h <fqdn>  -s -e \"select version();\"' returned 1. ERROR 2003 (HY000): Can't connect to MySQL server on '<fqdn>' (111)"

src[1]="2015-11-19 09:59:59 - Execution of 'mysql -u root --password=somep@ssword! -h myHost.internal  -s -e \"select version();\"' returned 1. ERROR 2003 (HY000): Can't connect to MySQL server on 'host.domain.com' (111)"
dest[1]="2015-11-19 09:59:59 - Execution of 'mysql -u root --password=<password> -h <fqdn>  -s -e \"select version();\"' returned 1. ERROR 2003 (HY000): Can't connect to MySQL server on '<fqdn>' (111)"

src[2]='File "/var/lib/ambari-agent/cache/common-services/RANGER/0.4.0/package/scripts/ranger_admin.py", line 124, in <module>'
dest[2]='File "/var/lib/ambari-agent/cache/common-services/RANGER/0.4.0/package/scripts/ranger_admin.py", line 124, in <module>'

src[3]='File "/usr/lib/python2.6/site-packages/resource_management/libraries/script/script.py", line 218, in execute'
dest[3]='File "/usr/lib/python2.6/site-packages/resource_management/libraries/script/script.py", line 218, in execute'

src[4]='resource_management.core.exceptions.Fail: Ranger Database connection check failed'
dest[4]='resource_management.core.exceptions.Fail: Ranger Database connection check failed'

src[5]='21 Sep 2015 02:28:45,580  INFO [qtp-ambari-agent-6292] HeartBeatHandler:657 - State of service component MYSQL_SERVER of service HIVE of cluster ...'
dest[5]='21 Sep 2015 02:28:45,580  INFO [qtp-ambari-agent-6292] HeartBeatHandler:657 - State of service component MYSQL_SERVER of service HIVE of cluster ...'

src[6]='21 Sep 2015 14:54:44,811  WARN [ambari-action-scheduler] ActionScheduler:311 - Operation completely failed, aborting request id:113'
dest[6]='21 Sep 2015 14:54:44,811  WARN [ambari-action-scheduler] ActionScheduler:311 - Operation completely failed, aborting request id:113'

src[7]="curl  -iuadmin:'mysecret' 'http://myServer:8080/...'"
dest[7]="curl  -iu<user>:<password> 'http://<hostname>:8080/...'"

src[8]="curl  -u admin:mysecret 'http://myServer:8080/...'"
dest[8]="curl  -u <user>:<password> 'http://<hostname>:8080/...'"

src[9]="curl  -u admin:'my secret' 'http://myServer:8080/...'"
dest[9]="curl  -u <user>:<password> 'http://<hostname>:8080/...'"

src[10]="curl  -u admin:\"my secret\" 'http://myServer:8080/...'"
dest[10]="curl  -u <user>:<password> 'http://<hostname>:8080/...'"

src[11]="curl -u=admin:'mysecret' 'http://myServer:8080/...'"
dest[11]="curl -u=<user>:<password> 'http://<hostname>:8080/...'"

src[12]=" main.py:74 - loglevel=logging.INFO"
dest[12]=" main.py:74 - loglevel=logging.INFO"

# creating an exception for this would prevent anonymization legitimate .PY domains after a leading timestamp, which is legit, added main.py to
src[13]="INFO 1111-22-33 44:55:66,777 main.py:8 -  Connecting to Ambari server at https://ip-1-2-3-4.eu-west-1.compute.internal:8440 (1.2.3.4)"
dest[13]="INFO 1111-22-33 44:55:66,777 main.py:8 -  Connecting to Ambari server at https://<fqdn>:8440 (<ip>)"

src[14]=" Connecting to Ambari server at https://ip-1-2-3-4.eu-west-1.compute.internal:8440 (1.2.3.4)"
dest[14]=" Connecting to Ambari server at https://<fqdn>:8440 (<ip>)"

src[15]="INFO 2015-12-01 19:52:21,066 DataCleaner.py:39 - Data cleanup thread started"
dest[15]="INFO 2015-12-01 19:52:21,066 DataCleaner.py:39 - Data cleanup thread started"

src[16]="INFO 2015-12-01 22:47:42,273 scheduler.py:287 - Adding job tentatively"
dest[16]="INFO 2015-12-01 22:47:42,273 scheduler.py:287 - Adding job tentatively"

src[17]="/usr/hdp/2.3.0.0-2557"
dest[17]="/usr/hdp/2.3.0.0-2557"

# can't safely prevent this without potentially exposing real IPs
#src[18]="/usr/hdp/2.3.0.0"
#dest[18]="/usr/hdp/2.3.0.0"

src[19]="ranger-plugins-audit-0.5.0.2.3.0.0-2557.jar"
dest[19]="ranger-plugins-audit-0.5.0.2.3.0.0-2557.jar"

src[20]="yarn-yarn-resourcemanager-ip-172-31-1-2.log"
dest[20]="yarn-yarn-resourcemanager-<aws_hostname>.log"

src[21]="192.168.99.100:9092"
dest[21]="<ip>:9092"

src[22]="192.168.99.100"
dest[22]="<ip>"

src[23]="openssl req ... -passin hari:mypassword ..."
dest[23]="openssl req ... -passin <password> ..."

src[24]="2018-01-01T00:00:00 INFO user=hari"
dest[24]="2018-01-01T00:00:00 INFO user=<user>"

src[25]="BigInsight:4.2"
dest[25]="BigInsight:4.2"

src[26]="user: hari, password: foo bar"
dest[26]="user: <user>, password: <password> bar"

src[27]="SomeClass\$method:20 something happened"
dest[27]="SomeClass\$method:20 something happened"

#src[28]="-passphase 'foo'"
#dest[28]="-passphrase '<password>'"

args="-aPe"
test_anonymize(){
    src="$1"
    dest="$2"
    #[ -z "${src[$i]:-}" ] && { echo "skipping test $i..."; continue; }
    result="$(./anonymize.py $args <<< "$src")"
    if grep -Fq "$dest" <<< "$result"; then
        echo "SUCCEEDED anonymization test $i"
    else
        echo "FAILED to anonymize line during test $i"
        echo "input:    $src"
        echo "expected: $dest"
        echo "got:      $result"
        exit 1
    fi
}

if [ -n "$test_num" ]; then
    grep -q '^[[:digit:]]\+$' <<< "$test_num" || { echo "invalid test '$test_num', not a positive integer"; exit 2; }
    i=$test_num
    [ -n "${src[$i]:-}" ]  || { echo "invalid test number given: src[$i] not defined"; exit 1; }
    [ -n "${dest[$i]:-}" ] || { echo "code error: dest[$i] not defined"; exit 1; }
    test_anonymize "${src[$i]}" "${dest[$i]}"
    exit 0
fi

# suport sparse arrays so that we can easily comment out any check pair for convenience
# this gives the number of elements and prevents testing the last element(s) if commenting something out in the middle
#for (( i = 0 ; i < ${#src[@]} ; i++ )); do
run_tests(){
    test_numbers="${@:-${!src[@]}}"
    for i in $test_numbers; do
        [ -n "${src[$i]:-}" ]  || { echo "code error: src[$i] not defined";  exit 1; }
        [ -n "${dest[$i]:-}" ] || { echo "code error: dest[$i] not defined"; exit 1; }
        if [ -n "$parallel" ]; then
            test_anonymize "${src[$i]}" "${dest[$i]}" &
        else
            test_anonymize "${src[$i]}" "${dest[$i]}"
        fi
    done
}
run_tests

# test ip prefix
src="4.3.2.1"
dest="<ip_prefix>.1"
result="$(./anonymize.py --ip-prefix <<< "$src")"
if grep -Fq "<ip_prefix>.1" <<< "$result"; then
    echo "SUCCEEDED anonymization test ip_prefix"
else
    echo "FAILED to anonymize line during test ip_prefix"
    echo "input:    $src"
    echo "expected: $dest"
    echo "got:      $result"
    exit 1
fi

# check normal don't strip these
src[101]="reading password from foo"
dest[101]="reading password from foo"

src[102]="some description = blah, module = foo"
dest[102]="some description = blah, module = foo"

args="-Hiukex"
run_tests 101 102

# now check --network / --cisco / --juniper do strip these
src[103]="reading password from bar"
dest[103]="reading password <cisco_password>"

src[104]="some description = blah, module=bar"
dest[104]="some description <cisco_description>"

args="--network"
run_tests 103 104

if [ -n "$parallel" ]; then
    # can't trust exit code for parallel yet, only for quick local testing
    exit 1
#    for i in ${!src[@]}; do
#        let j=$i+1
#        wait %$j
#        [ $? -eq 0 ] || { echo "FAILED"; exit $?; }
#    done
fi

echo "checking file args"
if [ `./anonymize.py -ae README.md | wc -l` -lt 100 ]; then
    echo "Suspicious readme file arg result came to < 100 lines"
    exit 1
fi

exit 0

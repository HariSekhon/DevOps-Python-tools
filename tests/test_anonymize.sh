#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-07-28 18:47:41 +0100 (Tue, 28 Jul 2015)
#
#  https://github.com/harisekhon/devops-python-tools
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

anonymize="./anonymize.py"

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
dest[13]="INFO 1111-22-33 44:55:66,777 main.py:8 -  Connecting to Ambari server at https://<fqdn>:8440 (<ip_x.x.x.x>)"

src[14]=" Connecting to Ambari server at https://ip-1-2-3-4.eu-west-1.compute.internal:8440 (1.2.3.4)"
dest[14]=" Connecting to Ambari server at https://<fqdn>:8440 (<ip_x.x.x.x>)"

src[15]="INFO 2015-12-01 19:52:21,066 DataCleaner.py:39 - Data cleanup thread started"
dest[15]="INFO 2015-12-01 19:52:21,066 DataCleaner.py:39 - Data cleanup thread started"

src[16]="INFO 2015-12-01 22:47:42,273 scheduler.py:287 - Adding job tentatively"
dest[16]="INFO 2015-12-01 22:47:42,273 scheduler.py:287 - Adding job tentatively"

src[17]="/usr/hdp/2.3.0.0-2557"
dest[17]="/usr/hdp/2.3.0.0-2557"

# can't safely prevent this without potentially exposing real IPs
#src[18]="/usr/hdp/2.3.0.0"
#dest[18]="/usr/hdp/2.3.0.0"
src[18]="hari/blah@realm"
dest[18]="<user>/<instance>@<domain>"

src[19]="ranger-plugins-audit-0.5.0.2.3.0.0-2557.jar"
dest[19]="ranger-plugins-audit-0.5.0.2.3.0.0-2557.jar"

src[20]="yarn-yarn-resourcemanager-ip-172-31-1-2.log"
dest[20]="yarn-yarn-resourcemanager-<aws_hostname>.log"

src[21]="192.168.99.100:9092"
dest[21]="<ip_x.x.x.x>:9092"

src[22]="192.168.99.100"
dest[22]="<ip_x.x.x.x>"

src[23]="openssl req ... -passin hari:mypassword ..."
dest[23]="openssl req ... -passin <password> ..."

src[24]="2018-01-01T00:00:00 INFO user=hari"
dest[24]="2018-01-01T00:00:00 INFO user=<user>"

src[25]="BigInsight:4.2"
dest[25]="BigInsight:4.2"

src[26]="user: hari, password: foo bar"
dest[26]="user: <user> password: <password> bar"

src[27]="SomeClass\$method:20 something happened"
dest[27]="SomeClass\$method:20 something happened"

#src[28]="-passphase 'foo'"
#dest[28]="-passphrase '<password>'"

src[29]=" at host.domain.com(Thread.java:789)"
dest[29]=" at host.domain.com(Thread.java:789"

src[30]="jdbc:hive2://hiveserver2:10000/myDB"
dest[30]="jdbc:hive2://<hostname>:10000/myDB"

src[31]="http://blah"
dest[31]="http://<hostname>"

src[32]="https://blah:443/path"
dest[32]="https://<hostname>:443/path"

src[33]="tcp://blah:8080"
dest[33]="tcp://<hostname>:8080"

src[34]="A1:B2:C3:D4:E4:F6"
dest[34]="<mac>"

src[35]="A1-B2-C3-D4-E4-F6"
dest[35]="<mac>"

src[36]='\\blah'
dest[36]='\\<hostname>'

src[37]='\\blah\path\to\data'
dest[37]='\\<hostname>\path\to\data'

src[38]='MYDOMAIN\hari'
dest[38]='<domain>\<user>'

src[39]="S-1-5-21-3623811015-3361044348-30300820-1013"
dest[39]="<windows_SID>"

src[40]="hari/host.domain.com@REALM.COM"
dest[40]="<user>/<instance>@<domain>"

src[41]="host/host.domain.com@REALM.ORG"
dest[41]="host/<instance>@<domain>"

src[42]="hive/_HOST@REALM.NET"
dest[42]="<user>/_HOST@<domain>"

src[43]="hdfs/HTTP@REALM.COM"
dest[43]="<user>/HTTP@<domain>"

src[44]="/tmp/krb5cc_12345"
dest[44]="/tmp/krb5cc_<uid>"

src[45]=" --user=hari"
dest[45]=" --user=<user>"

src[45]=" --group-name=techies"
dest[45]=" --group-name=<group>"

src[46]=" 1.2.3.4/24"
dest[46]=" <ip_x.x.x.x>/<cidr_mask>"

src[47]="blah@MyREALM1"
dest[47]="<user>@<domain>"

src[48]="@MyREALM"
dest[48]="@<domain>"

src[49]="hari@"
dest[49]="<user>@"

# LDAP too many tests!!
src[50]="CN=Hari Sekhon,OU=MyOU,DC=MyDomain,DC=com"
dest[50]="CN=<cn>,OU=<ou>,DC=<dc>,DC=<dc>"

src[51]="Ou=blah"
dest[51]="Ou=<ou>"

src[52]="DC=blah"
dest[52]="DC=<dc>"

src[53]="dn: CN=Hari Sekhon,OU=My OU,DC=MyDomain,DC=com"
#dest[53]="dn: CN=<cn>,OU=<ou>,DC=<dc>,DC=<dc>"
dest[53]="dn: <dn>"

src[54]="cn: Hari Sekhon"
dest[54]="cn: <cn>"

src[55]="sn: Sekhon"
dest[55]="sn: <sn>"

src[56]="title: Awesome Techie"
dest[56]="title: <title>"

src[57]="description: Awesome Techie"
dest[57]="description: <description>"

src[58]="givenName: Hari"
dest[58]="givenName: <givenname>"

src[59]="distinguishedName: CN=Hari Sekhon,OU=MyOU,DC=MyDomain,DC=com"
dest[59]="distinguishedName: <distinguishedname>"

src[60]="memberOf: CN=MyGroup1,OU=MyOU,OU=Ops,DC=MyDomain,DC=com"
dest[60]="memberOf: <memberof>"

src[61]="department: My IT Dept"
dest[61]="department: <department>"

src[62]="name: Hari Sekhon"
dest[62]="name: <name>"

src[63]="objectGUID:: a1b2c3d4T=="
dest[63]="objectGUID:: <objectguid>"

src[64]="primaryGroupID: 123"
dest[64]="primaryGroupID: <primarygroupid>"

src[65]="objectSid:: ABCDEF12345678+RmG+abcdef12345678=="
dest[65]="objectSid:: <objectsid>"

src[66]="sAMAccountName: hari"
dest[66]="sAMAccountName: <samaccountname>"

#src[67]="sAMAccountName: hari"
#dest[67]="sAMAccountName: <sAMAccountName>"

src[68]="objectCategory: CN=Person,CN=Schema,CN=Configuration,DC=MyDomain,DC=com"
#dest[68]="objectCategory: CN=Person,CN=Schema,CN=Configuration,DC=<domain>,DC=<domain>"
dest[68]="objectCategory: <objectcategory>"

src[69]="msDS-AuthenticatedAtDC: CN=MyDC1,OU=Domain Controllers,DC=MyDomain,DC=com"
#dest[69]="msDS-AuthenticatedAtDC: <msDS-AuthenticatedAtDC>"
dest[69]="msDS-AuthenticatedAtDC: CN=<cn>,OU=<ou>,DC=<dc>,DC=<dc>"

src[70]="uid: hari"
dest[70]="uid: <uid>"

src[71]="gidNumber: 10001"
dest[71]="gidNumber: <gidnumber>"

src[72]="uidNumber: 30001"
dest[72]="uidNumber: <uidnumber>"

src[73]="msSFU30Name: hari"
dest[73]="msSFU30Name: <mssfu30name>"

src[74]="msSFU30NisDomain: MyDomain"
#dest[74]="msSFU30NisDomain: <domain>"
dest[74]="msSFU30NisDomain: <mssfu30nisdomain>"

src[75]="unixHomeDirectory: /home/hari"
dest[75]="unixHomeDirectory: /home/<user>"

src[76]="member: CN=Hari Sekhon,OU=MyOU,DC=MyDomain,DC=com"
#dest[76]="member: CN=<cn>"
dest[76]="member: <member>"

src[77]="adminDisplayName: Administrator"
dest[77]="adminDisplayName: <admindisplayname>"

# TODO
#src[77]="ldap:///dc=example,dc=com??sub?(givenName=John)"
#dest[77]="ldap:///dc=<dc>,dc=<dc>??sub?(givenName=<givenName>)"

#src[78]="ldap://ldap.example.com/cn=John%20Doe,dc=example,dc=com"
#dest[78]="ldap://<fqdn>/cn=<cn>,dc=<dc>,dc=<dc>"

src[79]="userPassword=mysecret"
#dest[79]="userPassword=<userpassword>"
dest[79]="userPassword=<password>"

src[80]=" Authorization: Basic 123456ABCDEF"
dest[80]=" Authorization: Basic <token>"

src[81]="https://mylonggithubtoken@github.com/harisekhon/nagios-plugins"
dest[81]="https://<user>@<domain>/<custom>/nagios-plugins"

# --ldap attribute matches are done before --user matches
src[82]="uid=hari"
dest[82]="uid=<uid>"

args="-aPe"
test_anonymize(){
    src="$1"
    dest="$2"
    #[ -z "${src[$i]:-}" ] && { echo "skipping test $i..."; continue; }
    result="$($anonymize $args <<< "$src")"
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
run_tests  # ignore_run_unqualified

# test ip prefix
src="4.3.2.1"
dest="<ip_x.x.x>.1"
result="$($anonymize --ip-prefix <<< "$src")"
if grep -Fq "<ip_x.x.x>.1" <<< "$result"; then
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

args="-HKEiux"
run_tests 101 102  # ignore_run_unqualified

# now check --network / --cisco / --juniper do strip these
src[103]="reading password from bar"
dest[103]="reading password <cisco_password>"

src[104]="some description = blah, module=bar"
dest[104]="some description <cisco_description>"

args="--network"
run_tests 103 104  # ignore_run_unqualified

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
if [ `$anonymize -ae README.md | wc -l` -lt 100 ]; then
    echo "Suspicious readme file arg result came to < 100 lines"
    exit 1
fi
echo

echo "testing --email replacememnt format"
run_grep "<user>@<domain>" $anonymize -E <<< "hari@domain.com"
echo

echo "All Anonymize tests succeeded!"

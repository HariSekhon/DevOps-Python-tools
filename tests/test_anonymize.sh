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

test_nums="${*:-}"
#parallel=""
#if [ "$test_nums" = "p" ]; then
#    parallel="1"
#    test_nums=""
#fi

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

section "Anonymize"

anonymize="./anonymize.py"

start_time="$(start_timer "$anonymize")"

# ============================================================================ #
#                                  Custom Tests
# ============================================================================ #

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
dest[13]="INFO 1111-22-33 44:55:66,777 main.py:8 -  Connecting to Ambari server at https://<ip-x-x-x-x>.<fqdn>:8440 (<ip_x.x.x.x>)"

src[14]=" Connecting to Ambari server at https://ip-1-2-3-4.eu-west-1.compute.internal:8440 (1.2.3.4)"
dest[14]=" Connecting to Ambari server at https://<ip-x-x-x-x>.<fqdn>:8440 (<ip_x.x.x.x>)"

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
dest[20]="yarn-yarn-resourcemanager-<ip-x-x-x-x>.log"

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

src[28]="-passphrase 'foo'"
dest[28]="-passphrase <password>"

src[29]=" at host.domain.com(Thread.java:789)"
dest[29]=" at host.domain.com(Thread.java:789)"

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

src[67]="sAMAccountName: hari"
dest[67]="sAMAccountName: <samaccountname>"

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
#dest[76]="member: CN=<cn>,OU=<ou>,DC=<dc>,DC=<dc>"
dest[76]="member: <member>"

src[77]="adminDisplayName: Administrator"
dest[77]="adminDisplayName: <admindisplayname>"

src[78]="ldap://ldap.example.com/cn=John%20Doe,dc=example,dc=com"
dest[78]="ldap://<fqdn>/cn=<cn>,dc=<dc>,dc=<dc>"

src[79]="userPassword=mysecret"
#dest[79]="userPassword=<userpassword>"
dest[79]="userPassword=<password>"

src[80]=" Authorization: Basic 123456ABCDEF"
dest[80]=" Authorization: Basic <token>"

src[81]="https://mylonggithubtoken@github.com/harisekhon/nagios-plugins"
dest[81]="https://<user>@<domain>/<custom>/nagios-plugins"

# --ldap attribute matches are done before --user matches
src[82]="uid = hari"
dest[82]="uid = <uid>"

src[83]=" --group-name=techies"
dest[83]=" --group-name=<group>"

src[84]="ldap:///dc=example,dc=com??sub?(givenName=John)"
dest[84]="ldap:///dc=<dc>,dc=<dc>??sub?(givenName=<givenname>)"

# check we don't replace IP type things that are not really IPs because too many octets
src[85]="ip-1-2-3-4-5"
dest[85]="ip-1-2-3-4-5"

src[86]="dip-1-2-3-4"
dest[86]="dip-1-2-3-4"

src[87]="1.2.3.4.5"
dest[87]="1.2.3.4.5"

src[88]="-host blah"
dest[88]="-host <hostname>"

src[89]="--hostname=blah --anotherswitch"
dest[89]="--hostname=<hostname> --anotherswitch"

src[90]="host=test"
dest[90]="host=<hostname>"

src[91]="host went away"
dest[91]="host went away"

src[92]="hostname=blah;port=92"
dest[92]="hostname=<hostname>;port=92"

# check we replace all occurences along line
src[93]="hari@domain.com, hari@domain2.co.uk"
dest[93]="<user>@<domain>, <user>@<domain>"

src[94]="spark://hari@192.168.0.1"
dest[94]="spark://<user>@<ip_x.x.x.x>"

src[95]="/usr/hdp/2.6.2.0-123/blah"
dest[95]="/usr/hdp/2.6.2.0-123/blah"

src[96]="log4j-1.2.3.4.jar"
dest[96]="log4j-1.2.3.4.jar"

src[97]='MYDOMAIN\n2018-10-03 01:23:45'
dest[97]='MYDOMAIN\n2018-10-03 01:23:45'

src[98]='domain789012345\blah'
dest[98]='<domain>\<user>'

src[99]='domain7890123456\blah'
dest[99]='domain7890123456\blah'

src[100]="-Dhost=blah"
dest[100]="-Dhost=<hostname>"

src[101]="-Ddomain.com=blah"
dest[101]="-Ddomain.com=blah"

src[102]="-Dhost.domain.com=blah"
dest[102]="-Dhost.domain.com=blah"

# check escape codes get stripped if present (eg. if piping from grep --color-yes)
# breaks test_anonymize.py which doesn't eval this, so put it explicitly
#src[103]="$(echo somehost:443 | grep --color=yes host)"
src[103]="some[01;31m[Khost[m[K:443"
dest[103]="<hostname>:443"

src[104]='..., "user": "blah", "group": "blah2", "host": "blah3", ...'
dest[104]='..., "user": "<user>", "group": "<group>", "host": "<hostname>", ...'

src[105]='...,"owner":"blah","hostname":"blah2",...'
dest[105]='...,"owner":"<user>","hostname":"<hostname>",...'

src[106]="ambari-sudo.sh"
dest[106]="ambari-sudo.sh"

src[107]="hdfs://user/blah"
dest[107]="hdfs://<hostname>/<user>"

src[108]="hdfs:///user/blah"
dest[108]="hdfs:///user/<user>"

src[109]="es.xpack.user=hari"
dest[109]="es.xpack.user=<user>"

src[110]="es.xpack.password=myp@ss!"
dest[110]="es.xpack.password=<password>"

src[111]="127.0.0.1"
dest[111]="127.0.0.1"

src[112]="travis token:  Abc123"
dest[112]="travis token:  <token>"

src[113]="arn:aws:iam::123456789012:user/hari"
dest[113]="arn:aws:iam::<account_id>:user/<user>"

src[114]="arn:aws:iam::123456789012:group/hari"
dest[114]="arn:aws:iam::<account_id>:group/<group>"

src[115]="arn:aws:iam::123456789012:user/Development/product_1234/*"
dest[115]="arn:aws:iam::<account_id>:user/<user>/*"

src[116]="arn:aws:iam::123456789012:group/Development/product_1234/*"
dest[116]="arn:aws:iam::<account_id>:group/<group>/*"

src[117]="arn:aws:iam::123456789012:group/Development/product_1234/*"
dest[117]="arn:aws:iam::<account_id>:group/<group>/*"

src[118]="arn:aws:s3:::my_corporate_bucket/Development/*"
dest[118]="arn:aws:s3:::<resource>*"

src[119]="AKIAIOSFODNN7EXAMPLE"
dest[119]="<access_key>"

src[120]="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
dest[120]="<secret_key>"

src[121]="AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE"
dest[121]="<sts_token>"

src[122]="ASIAIOSFODNN7EXAMPLE"
dest[122]="<sts_access_key>"

src[123]="AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGdQrmGdeehM4IC1NtBmUpp2wUE8phUZampKsburEDy0KPkyQDYwT7WZ0wq5VSXDvp75YU9HFvlRd8Tx6q6fE8YQcHNVXAkiY9q6d+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA=="
dest[123]="<sts_token>"

# security groups
src[124]="sg-5f63c627"
dest[124]="<sg-xxxxxxxx>"

src[125]="s3://myBucket/file.txt"
dest[125]="s3://<bucket>/file.txt"

src[126]="aws rds create-db-instance --db-name myDB"
dest[126]="aws rds create-db-instance --db-name <database>"

src[127]="aws rds modify-db-instance --db-instance-identifier myDBinstance"
dest[127]="aws rds modify-db-instance --db-instance-identifier <database_instance>"

src[128]="--master-user-password blah"
dest[128]="--master-user-password <password>"

src[129]="--master-username first.last"
dest[129]="--master-username <username>"

src[130]="--schema-name mySchema"
dest[130]="--schema-name <schema>"

src[131]="=arn:aws:acm:us-east-1:123456:certificate/abc-123"
dest[131]="=arn:aws:acm:us-east-1:<account_id>:certificate/<certificate>"

src[132]="--key-name my-key"
dest[132]="--key-name <key>"

src[133]="-private-key my-key"
dest[133]="-private-key <key>"

src[134]="aws elasticache create-cache-cluster --cache-cluster-id myCluster"
dest[134]="aws elasticache create-cache-cluster --cache-cluster-id <cluster>"

src[135]="subnet-abc12345"
dest[135]="<subnet-xxxxxxxx>"

src[136]="arn:aws:acm:us-east-1:123456:function:myFunction123:7"
dest[136]="arn:aws:acm:us-east-1:<account_id>:function:<function>:7"

src[137]="aws lambda update-function-code --function-name hari-test --zip-file fileb://myfunction.zip"
dest[137]="aws lambda update-function-code --function-name <function> --zip-file fileb://<file>"

# shellcheck disable=SC2016
src[138]=' aws elb create-load-balancer --load-balancer-name "$lb_name" ...'
dest[138]=' aws elb create-load-balancer --load-balancer-name <load_balancer_name> ...'

src[139]=' in column "blah" of table "blah2"'
dest[139]=' in column "<column>" of table "<table>"'

src[140]='ssh -i myKey -N -L 8888:ec2-1-2-3-4.eu-west-1.compute.amazonaws.com:8888 hadoop@ec2-1-2-3-4.eu-west-1.compute.amazonaws.com'
# email anonymization applies before fqdn anonymization
#dest[140]='ssh -i myKey -N -L 8888:<fqdn>:8888 <user>@<fqdn>'
dest[140]='ssh -i myKey -N -L 8888:<fqdn>:8888 <user>@<domain>'

src[141]="Failed to open HDFS file hdfs://nameservice1/user/hive/warehouse/area_2/my_database_2.db/my_table_2/part-r-00030-6a789012-3bc4-56d7-e890-123fa456b7c8.snappy.parquet\nError(2): No such file or directory"
dest[141]="Failed to open HDFS file hdfs://<hostname>/user/<user>/warehouse/<database>.db/<table>/part-r-00030-6a789012-3bc4-56d7-e890-123fa456b7c8.snappy.parquet\nError(2): No such file or directory"

src[142]="ERROR: AnalysisException: Failed to load metadata for table: 'myCustomerTable2'"
dest[142]="ERROR: AnalysisException: Failed to load metadata for table: '<table>'"

src[143]="PS /pwd> Connect-AppVeyorToComputer -AppVeyorUrl https://ci.appveyor.com -ApiToken a12bcdef3a45b6cdefab"
dest[143]="PS /pwd> Connect-AppVeyorToComputer -AppVeyorUrl https://<fqdn> -ApiToken <token>"


# TODO: move proxy hosts to host matches and re-enable
#src[103]="proxy blah port 8080"
#dest[103]="proxy <proxy_host> port <proxy_port>"

#src[104]="Connected to blah (1.2.3.4) port 8080"
#dest[104]="Connected to <proxy_host> (<proxy_ip>) port <proxy_port>"

args="-aPe"
test_anonymize(){
    run++
    # shellcheck disable=SC2178
    local src="$1"
    # shellcheck disable=SC2178
    local dest="$2"
    #[ -z "${src[$i]:-}" ] && { echo "skipping test $i..."; continue; }
    # didn't work for \e escape codes for ANSI stripping test
    #result="$(echo -e "$src" | $anonymize $args)"
    # shellcheck disable=SC2128
    result="$($anonymize $args <<< "$src")"
    # shellcheck disable=SC2128
    if grep -xFq -- "$dest" <<< "$result"; then
        echo -n "SUCCEEDED anonymization test $i"
        if [ -n "${SHOW_OUTPUT:-}" ]; then
            echo " => $dest"
        else
            echo
        fi
    else
        echo "FAILED to anonymize line during test $i"
        echo "input:    $src"
        echo "expected: $dest"
        echo "got:      $result"
        exit 1
    fi
}

if [ -n "$test_nums" ]; then
    for test_num in $test_nums; do
        grep -q -- '^[[:digit:]]\+$' <<< "$test_num" || { echo "invalid test '$test_num', not a positive integer"; exit 2; }
        i=$test_num
        [ -n "${src[$i]:-}" ]  || { echo "invalid test number given: src[$i] not defined"; exit 1; }
        [ -n "${dest[$i]:-}" ] || { echo "code error: dest[$i] not defined"; exit 1; }
        test_anonymize "${src[$i]}" "${dest[$i]}"
    done
    exit 0
fi

# suport sparse arrays so that we can easily comment out any check pair for convenience
# this gives the number of elements and prevents testing the last element(s) if commenting something out in the middle
#for (( i = 0 ; i < ${#src[@]} ; i++ )); do
run_tests(){
    # expands to the list of indicies in the array, starting at zero - this is easier to work with that ${#src} which is a total
    # that is off by one for index usage and doesn't support sparse arrays for any  missing/disabled test indicies
    test_numbers="${*:-${!src[*]}}"
    for i in $test_numbers; do
        [ -n "${src[$i]:-}" ]  || { echo "code error: src[$i] not defined";  exit 1; }
        [ -n "${dest[$i]:-}" ] || { echo "code error: dest[$i] not defined"; exit 1; }
        #test_anonymize "${src[$i]}" "${dest[$i]}"
        run++
    done
    "$srcdir/test_anonymize.py"
}

#echo
#echo "Running Standard Tests with --all --skip-exceptions"
#echo
run_tests "$@" # ignore_run_unqualified

#echo
#echo "Running Tests preseving text without --network enabled:"
#echo
# check normal don't strip these
src[901]="reading password from foo"
dest[901]="reading password from foo"

src[902]="some description = blah, module = foo"
dest[902]="some description = blah, module = foo"

args="-HKEiu"
#run_tests 901 902  # ignore_run_unqualified

#echo
#echo "Running Network Specific Tests:"
#echo
# now check --network / --cisco / --juniper do strip these
src[903]="reading password from bar"
dest[903]="reading password <cisco_password>"

src[904]="some description = blah, module=bar"
dest[904]="some description <cisco_description>"

args="--network"
#run_tests 903 904  # ignore_run_unqualified

#if [ -n "$parallel" ]; then
#    # can't trust exit code for parallel yet, only for quick local testing
#    exit 1
##    for i in ${!src[@]}; do
##        let j=$i+1
##        wait %$j
##        [ $? -eq 0 ] || { echo "FAILED"; exit $?; }
##    done
#fi

# ============================================================================ #

if [ -z "$test_nums" ]; then
    echo
    echo "Running Custom Tests:"
    echo
    echo "checking file args:"
    run++
    if [ "$($anonymize -ae README.md | wc -l)" -gt 100 ]; then
        echo "SUCCEEDED - anonymized README.md > 100 lines"
    else
        echo "FAILED - suspicious README.md file arg result came to <= 100 lines"
        exit 1
    fi
    hr

    run_grep "<user>@<domain>" $anonymize --email <<< "hari@domain.com"
    run_grep "<user>@<domain>" $anonymize -E <<< "hari@domain.com"

    src[800]="4.3.2.1"
    dest[800]="<ip_x.x.x>.1"

    src[801]="4.3.2.1/24"
    dest[801]="<ip_x.x.x>.1/<cidr_mask>"

    src[802]="4.3.2.1"
    dest[802]="<ip_x.x.x>.1"

    src[803]="ip-1-2-3-4"
    dest[803]="<ip-x-x-x>.4"

    src[804]="ip-1-2-3-4-5"
    dest[804]="ip-1-2-3-4-5"

    src[805]="dip-1-2-3-4"
    dest[805]="dip-1-2-3-4"

    src[806]="5.4.3.2.1"
    dest[806]="5.4.3.2.1"

    src[807]="log4j-1.2.3.4.jar"
    dest[807]="log4j-1.2.3.4.jar"

    src[808]="/usr/hdp/2.6.2.0-123"
    dest[808]="/usr/hdp/2.6.2.0-123"
    args="-a --ip-prefix"

    run_grep "^http://[a-f0-9]{12}:80/path$" $anonymize --hash-hostnames <<< "http://test.domain.com:80/path"
    run_grep '^\\\\[a-f0-9]{12}\\mydir$' $anonymize --hash-hostnames <<< '\\test.domain.com\mydir'
    run_grep '-host [a-f0-9]{12}' $anonymize --hash-hostnames <<< '-host blah'
fi

echo
# run_count assigned in utils lib
# shellcheck disable=SC2154
echo "Total Tests run: $run_count"
time_taken "$start_time" "SUCCESS! All tests for $anonymize completed in"
echo

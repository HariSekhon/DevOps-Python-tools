#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-08-08 19:02:02 +0100 (Wed, 08 Aug 2018)
#  Original Date: 2013-07-18 21:17:41 +0100 (Thu, 18 Jul 2013)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  ported from Perl version from DevOps Perl Tools repo (https://github.com/harisekhon/devops-perl-tools)
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#


"""

Anonymizes usernames, passwords, IP addresses, hostnames, emails addresses, Company Name, Your Name(!)
from text logs or config files to make suitable for sharing in email with vendors, public tickets, Jiras
or pastebin like websites

Also has support for network device configurations including Cisco and Juniper,
and should work on devices with similar configs as well.

Works like a standard unix filter program, reading from file arguments or standard input and
printing the modified output to standard output (to redirect to a new file or copy buffer).

Create a list of phrases to anonymize from config by placing them in anonymize_custom.conf in the same directory
as this program, one PCRE format regex per line, blank lines and lines prefixed with # are ignored.

Ignore phrases are in a similar file anonymize_ignore.conf, also adjacent to this program.

Based on Perl Anonymize.pl from https://github.com/harisekhon/devops-perl-tools

The Perl version is incredibly faster than Python due to the better regex engine

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from hashlib import md5
import os
import re
import sys
import traceback
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import \
        isJavaException, \
        isPythonTraceback, \
        isPythonMinVersion, \
        isRegex, \
        isStr, \
        log, \
        log_option, \
        strip_ansi_escape_codes, \
        validate_file
    # used dynamically
    # pylint: disable=unused-import
    from harisekhon.utils import \
        aws_host_ip_regex, \
        domain_regex_strict, \
        filename_regex, \
        fqdn_regex, \
        host_regex, \
        hostname_regex, \
        ip_prefix_regex, \
        ip_regex, \
        subnet_mask_regex, \
        user_regex
    # used dynamically
    # pylint: disable=unused-import
    # lgtm [py/unused-import] - used by dynamic code so code analyzer cannot comprehend
    from harisekhon.utils import \
        domain_regex, \
        email_regex, \
        mac_regex \
        # lgtm [py/unused-import] - used by dynamic code so code analyzer cannot comprehend
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.10.12'

ip_regex = r'(?!127\.0\.0\.)' + ip_regex
subnet_mask_regex = r'(?!127\.0\.0\.)' + subnet_mask_regex

class Anonymize(CLI):

    def __init__(self):
        # Python 2.x
        super(Anonymize, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = None
        self.custom_anonymization_file = os.path.join(srcdir, 'anonymize_custom.conf')
        self.custom_ignore_file = os.path.join(srcdir, 'anonymize_ignore.conf')
        self.custom_anonymizations = set()
        self.custom_ignores = set()
        self.custom_ignores_raw = ''
        self.file_list = set()
        self.re_line_ending = re.compile(r'(\r?\n)$')
        self.strip_cr = False
        self.hash_salt = None
        # order of iteration of application matters because we must do more specific matches before less specific ones
        self.anonymizations = OrderedDict([
            ('ip_prefix', False),
            ('ip', False),
            ('subnet_mask', False),
            ('mac', False),
            ('db', False),
            ('generic', False),
            # kerberos must be applied before email
            # - if email is applied first, 'user/host@realm' becomes 'user/<email_regex>', exposing user
            ('kerberos', False),
            ('email', False),
            ('password', False),
            ('ldap', False),
            ('user', False),
            ('group', False),
            ('http_auth', False),
            ('cisco', False),
            ('screenos', False),
            ('junos', False),
            ('network', False),
            ('windows', False),
            ('aws', False),  # access key, secret key, sts tokens etc are very generic so do them later
            ('fqdn', False),
            ('domain', False),
            ('hostname', False),
            #('proxy', False),
            ('custom', False),
        ])
        self.exceptions = {
            'java_exceptions': False,
            'python_tracebacks': False,
        }
        # Poland is more prominent, cannot exclude .pl from host/domain/fqdn negative lookbehinds
        ignore_file_exts = ['java', 'py', 'sh', 'pid', 'scala', 'groovy']
        self.negative_host_lookbehind = ''.join(r'(?<!\.{})'.format(_) for _ in ignore_file_exts) + \
                                        r'(?<!\sid)'
        ldap_rdn_list = [
            # country isn't exactly secret information worth anonymizing in most cases
            #'C',
            'CN',
            'DC',
            'L',
            'O',
            'OU',
            'ST',
            'STREET',
            'UID',
        ]
        # hard for this to be 100% since this can be anything backslash escaped but getting what we really care about
        ldap_values = r'[\\\%\s\w-]+'
        # AD user + group objects - from real world sample
        ldap_attributes = [
            'cn',
            'department',
            'description',
            'distinguishedName',
            'dn',
            'gidNumber',
            'givenName',
            'homeDirectory',
            'member',
            'memberOf',
            'msSFU30Name',
            'msSFU30NisDomain',
            'name',
            'objectCategory',
            'objectGUID',
            'objectSid',
            'primaryGroupID',
            'sAMAccountName',
            'sn',
            'title',
            'uid',
            'uidNumber',
            # let /home/hari => /home/<user>
            #'unixHomeDirectory',
        ]
        # IPA / OpenLDAP attributes
        # http://www.zytrax.com/books/ldap/ape/
        ldap_attributes.extend([
            'userPassword',
            'gn',
            'mail',
            'surname',
            #'localityName'  # city, same as l below
            'facsimileTelephoneNumber',
            'rfc822Mailbox',
            'homeTelephoneNumber',
            'pagerTelephoneNumber',
            'uniqueMember',
        ])
        # From documentation of possible standard attributes
        # https://docs.microsoft.com/en-us/windows/desktop/ad/group-objects
        # http://www.kouti.com/tables/userattributes.htm
        # https://docs.microsoft.com/en-us/windows/desktop/adschema/attributes-all
        extra_ldap_attribs = [
            # this will be a CN, let general case strip it
            #'msDS-AuthenticatedAtDC'
            'adminDescription',
            'adminDisplayName',
            'canonicalName',
            'comment',
            #'co', # (country)
            #'countryCode',
            'displayName',
            'displayNamePrintable',
            'division',
            'employeeID',
            'groupMembershipSAM',
            'info',
            'initials',
            #'l' # city
            'logonWorkstation',
            'manager',
            'middleName',
            'mobile',
            'otherHomePhone',
            'otherIpPhone',
            'otherLoginWorkstations',
            'otherMailbox',
            'otherMobile',
            'otherPager',
            'otherTelephone',
            'pager',
            'personalTitle',
            'physicalDeliveryOfficeName',
            'possibleInferiors',
            'postalAddress',
            'postalCode',
            'postOfficeBox',
            'preferredOU',
            'primaryInternationalISDNNumber',
            'primaryTelexNumber',
            'profilePath',
            'proxiedObjectName',
            'proxyAddresses',
            'registeredAddress',
            'scriptPath',
            'securityIdentifier',
            'servicePrincipalName',
            'street',
            'streetAddress',
            'supplementalCredentials',
            'telephoneNumber',
            'teletexTerminalIdentifier',
            'telexNumber',
            'url',
            'userWorkstations',
            'wWWHomePage',
            'x121Address',
            'userCert',
            'userCertificate',
            'userParameters',
            'userPassword',
            'userPrincipalName',
            'userSharedFolder',
            'userSharedFolderOther',
            'userSMIMECertificate',
        ]
        # comment this line out for performance if you're positive you don't use these attributes
        ldap_attributes.extend(extra_ldap_attribs)
        # MSSQL ODBC
        #ldap_attributes.extend(['DatabaseName'])
        # Hive ODBC / JDBC
        #ldap_attributes.extend(['HS2KrbRealm', 'dbName'])
        # don't use this simpler one as we want to catch everything inside quotes eg. 'my secret'
        #password_quoted = r'\S+'
        password_quoted = r'(?:\'[^\']+\'|"[^"]+"|\S+)'
        user_name = r'(?:user(?:[_-]?name)?|uid)'
        group_name = r'group(?:-?name)?'
        arg_sep = r'[=\s:]+'
        # openssl uses -passin switch
        pass_word_phrase = r'(?:pass(?:word|phrase|in)?|userPassword)'
        # allowing --blah- prefix variants
        switch_prefix = r'(?<!\w)--?(?:[A-Za-z0-9-]+-)*'
        id_or_name = r'(?:-?(?:id|name|identifier))'
        self.regex = {
            # arn:partition:service:region:account-id:resource-id
            # arn:partition:service:region:account-id:resource-type/resource-id
            # arn:partition:service:region:account-id:resource-type:resource-id
            # eg. arn:aws:iam::123456789012:group/Development/product_1234/*
            'aws': r'\b(arn:[^:]+:[^:]+:[^:]*:)\d+(:([^:/]+)[:/])[\w/.-]+',
            # arn:aws:s3:::my_corporate_bucket/Development/*
            #'aws2': r'\b(arn:aws:s3:::)[^/]+',
            'aws2': r'\b(arn:[^:]+:[^:]+:[^:]*:)\d*:[\w/.-]+',
            # https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_identifiers.html
            'aws3': r'\bAKIA[A-Za-z0-9]{16}\b',  # access key
            'aws4': r'\b[A-Za-z0-9][A-Za-z0-9/+=-]{238,}',  # STS token - no \b at end as it'll stop before '==' suffix
            'aws5': r'\b[A-Za-z0-9][A-Za-z0-9/+=-]{38}[A-Za-z0-9]\b',  # secret key
            'aws6': r'\bASIA[A-Za-z0-9]{16}\b',  # sts temporary access key
            'aws7': r'\bsg-[A-Za-z0-9]{8}(?<!<sg-xxxxxxxx)(?!\w)', # security group id
            'aws8': r'(\bs3a?)://[^/]+/', # s3 bucket name
            'aws9': r'(?<!<)\bsubnet-[A-Za-z0-9]{8}\b',
            # would get double replaced to ec2-x-x-x-x.<region>.<fqdn> anyway by later fqdn anonymization
            #'aws10': r'ec2-\d+-\d+-\d+-\d+\.{region}(\.compute\.amazonaws\.com)'.format(region='[A-Za-z0-9-]+'),
            'db': r'({switch_prefix}(?:db|database)-?name{arg_sep})\S+'\
                   .format(arg_sep=arg_sep,
                           switch_prefix=switch_prefix),
            'db2': r'({switch_prefix}(?:db|database)-?instance{id_or_name}?{arg_sep})\S+'\
                   .format(arg_sep=arg_sep,
                           id_or_name=id_or_name,
                           switch_prefix=switch_prefix),
            'db3': r'({switch_prefix}schema{id_or_name}?{arg_sep})\S+'\
                   .format(arg_sep=arg_sep,
                           id_or_name=id_or_name,
                           switch_prefix=switch_prefix),
            'db4': r'(\s(?:in|of|for)\s+(column|table|database|schema)[\s:]+[\'"])[^\'"]+',
            'db5': r'/+user/+hive/+warehouse/+([A-Za-z0-9_-]+/+)*[A-Za-z0-9_-]+.db/+[A-Za-z0-9_-]+',
            'generic': r'(\bfileb?)://{filename_regex}'.format(filename_regex=filename_regex),
            'generic2': r'({switch_prefix}key{id_or_name}?{arg_sep})\S+'\
                   .format(arg_sep=arg_sep,
                           id_or_name=id_or_name,
                           switch_prefix=switch_prefix),
            'generic3': r'({switch_prefix}cluster{id_or_name}?{arg_sep})\S+'\
                   .format(arg_sep=arg_sep,
                           id_or_name=id_or_name,
                           switch_prefix=switch_prefix),
            'generic4': r'({switch_prefix}function{id_or_name}?{arg_sep})\S+'\
                   .format(arg_sep=arg_sep,
                           id_or_name=id_or_name,
                           switch_prefix=switch_prefix),
            'generic5': r'({switch_prefix}load-?balancer{id_or_name}?{arg_sep})\S+'\
                   .format(arg_sep=arg_sep,
                           id_or_name=id_or_name,
                           switch_prefix=switch_prefix),
            # don't change hostname or fqdn regex without updating hash_hostnames() option parse
            # since that replaces these replacements and needs to match the grouping captures and surrounding format
            'hostname2': r'({aws_host_ip})(?!-\d)'.format(aws_host_ip=aws_host_ip_regex),
            'hostname3': r'(\w+://)({hostname})'.format(hostname=hostname_regex),
            'hostname4': r'\\\\({hostname})'.format(hostname=hostname_regex),
            # no \bhost - want to match KrbHost
            'hostname5': r'(-host(?:name)?{sep}|host(?:name)?\s*=\s*)({hostname})'\
                         .format(sep=arg_sep, hostname=hostname_regex),
            'hostname6': r'(["\']host(?:name)?["\']\s*:\s*["\']?){hostname}'.format(hostname=hostname_regex),
            # use more permissive hostname_regex to catch Kerberos @REALM etc
            'domain2': '@{host}'.format(host=hostname_regex),
            'group': r'(-{group_name}{sep})\S+'.format(group_name=group_name, sep=arg_sep),
            'group2': r'({group_name}{sep}){user}'.format(group_name=group_name, sep=arg_sep, user=user_regex),
            'group3': r'for\s+group\s+{group}'.format(group=user_regex),
            'group4': r'(["\']{group_name}["\']\s*:\s*["\']?){group}'.format(group_name=group_name, group=user_regex),
            'group5': r'(arn:aws:iam:[^:]*:)\d+(:group/){group}'.format(
                group='({user_regex}/)*{user_regex}'.format(user_regex=user_regex)),
            'user': r'([-\.]{user_name}{sep})\S+'.format(user_name=user_name, sep=arg_sep),
            'user2': r'/(home|user)/{user}'.format(user=user_regex),
            'user3': r'({user_name}{sep}){user}'.format(user_name=user_name, sep=arg_sep, user=user_regex),
            'user4': r'(?<![\w\\]){NT_DOMAIN}(?!\\r|\\n)(?!\\n\d\d\d\d-\d\d-\d\d)\\{user}(?!\\)'\
                     .format(NT_DOMAIN=r'\b[\w-]{1,15}\b', user=user_regex),
            'user5': r'for\s+user\s+{user}'.format(user=user_regex),
            # (?<!>/) exclude patterns '>/' where we have already matched and token replaced
            'user6': r'(?<!<user>/){user}@'.format(user=user_regex),
            'user7': r'(["\'](?:{user_name}|owner)["\']\s*:\s*["\']?){user}'\
                     .format(user_name=user_name, user=user_regex),
            #'user8': r'arn:aws:iam::\d{12}:user/{user}'.format(user=user_regex),
            'user8': r'(arn:aws:iam:[^:]*:)\d+(:user/){user}'.format(
                user='({user_regex}/)*{user_regex}'.format(user_regex=user_regex)),
            'password': r'([\.-]?{pass_word_phrase}{sep}){pw}'\
                        .format(pass_word_phrase=pass_word_phrase,
                                sep=arg_sep,
                                pw=password_quoted),
            'password2': r'(\bcurl\s.*?-[A-Za-tv-z]*u[=\s]*)[^\s:]+:{pw}'.format(pw=password_quoted),
            'password3': r'\b({user}{sep})\S+([\,\.\s]+{pass_word_phrase}{sep}){pw}'\
                         .format(user=user_name,
                                 sep=arg_sep,
                                 pass_word_phrase=pass_word_phrase,
                                 pw=password_quoted),
            'password4': r'([\.-]?(?:api-?)?token{sep}){pw}'\
                         .format(sep=arg_sep,
                                 pw=password_quoted),
            'ip': r'(?<!\d\.)' + ip_regex + r'/\d{1,2}',
            'ip2': r'(?<!\d\.)' + ip_regex + r'(?!\w*[.-]\w)',
            'ip3': aws_host_ip_regex + r'(?!-)',
            'ip_prefix': r'(?<!\d\.)' + ip_prefix_regex + r'(\d+)/\d{1,2}',
            'ip_prefix2': r'(?<!\d\.)' + ip_prefix_regex + r'(\d+)(?!\w*[.-]\w)',
            'ip_prefix3': r'\bip-\d+-\d+-\d+-(\d+)(?!-)',
            'subnet_mask': r'(?<!\d\.)' + subnet_mask_regex + r'(?!-|\w*[.-:]\w)',
            # network device format Mac address
            'mac2': r'\b(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}\b',
            # _HOST and HTTP are commonly use in Hadoop clusters, let's make sure they are left for debugging purposes
            # must use hostname_regex to be permission enough to match @REALM since Krb5 realms do not have to be
            # domains even though they usually are
            'kerberos': r'\bhost/(_HOST|HTTP)@{realm}'.format(realm=hostname_regex),
            'kerberos2': r'\bhost/{instance}@{realm}'.format(instance=host_regex, realm=hostname_regex),
            'kerberos3': '{primary}/(_HOST|HTTP)@{realm}'.format(primary=user_regex, realm=hostname_regex),
            'kerberos4': r'{primary}/{instance}@{realm}'\
                         .format(primary=user_regex, instance=host_regex, realm=hostname_regex),
            'kerberos5': r'/krb5cc_\d+',
            # auto-enables --email to handle this instead now
            #'kerberos6': r'{primary}@{realm}'.format(primary=user_regex, realm=hostname_regex),
            # https://tools.ietf.org/html/rfc4514
            #'ldap': '(CN=)[^,]+(?:,OU=[^,]+)+(?:,DC=[\w-]+)+',
            # replace individual components instead
            'ldap': r'(\b({ldap_rdn_list})\s*[=:]+\s*)(?!(?:Person|Schema|Configuration),|\s){ldap_values}'\
                    .format(ldap_rdn_list='|'.join(ldap_rdn_list), ldap_values=ldap_values),
            'ldap2': r'^(\s*({ldap_attribs})\s*:+\s*).*$'\
                     .format(ldap_attribs='|'.join(ldap_attributes)),
            'ldap3': r'(\s*\b({ldap_attribs})\s*=\s*)(?!\s){ldap_values}'\
                     .format(ldap_attribs='|'.join(ldap_attributes), ldap_values=ldap_values),
            'port': r'{host}:\d+(?!\.?[\w-])'.format(host=host_regex),
            'proxy': r'proxy {} port \d+'.format(host_regex),
            'proxy2': 'Connected to ' + host_regex + r'\s*\(' + ip_regex + r'|[^\)]+\) port \d+',
            #'proxy3': r'(Via:\s\S+\s)' + ip_regex + '.*',
            'http_auth': r'(https?:\/\/)[^:]+:[^\@]*\@',
            'http_auth2': r'(Proxy auth using \w+ with user )([\'"]).+([\'"])',
            'http_auth3': r'\bAuthorization:\s+Basic\s+[A-Za-z0-9]+',
            'http_auth4': r'(\btoken:\s+)[A-Za-z0-9]+',
            'cisco': r'username .+ (?:password|secret) .*?$',
            'cisco2': r'password (?!<(?:cisco_)?password>).*?$',
            'cisco3': r'\ssecret\s.*?$',
            'cisco4': r'\smd5\s+.*?$',
            'cisco5': r'\scommunity\s+.*$',
            'cisco6': r'(standby\s+\d+\s+authentication).*',
            'cisco7': r'\sremote-as\s\d+',
            'cisco8': r'description\s.*$',
            'screenos': r'set admin (name|user|password) "?.+"?',
            'screenos2': r'set snmp (community|host) "?.+"?',
            'screenos3': r' md5 "?.+"?',
            'screenos4': r' key [^\s]+ (?:!enable)',
            'screenos5': r'set nsmgmt init id [^\s]+',
            'screenos6': r'preshare .+? ',
            'junos': r'pre-shared-key\s.*',
            'junos2': r'\shome\s+.*',
            'network': r'username .*',
            'network2': r'syscontact .*',
            'windows': r'S-\d+-\d+-\d+-\d+-\d+-\d+-\d+'
        }
        # dump computer generated regexes to debug complex regex
        #import pprint
        #pprint.pprint(self.regex)
        ldap_lambda_lowercase = lambda m: r'{}<{}>'.format(m.group(1), m.group(2).lower())
        # will auto-infer replacements to not have to be explicit, use this only for override mappings
        self.replacements = {
            # arn:partition:service:region:account-id:resource-id
            # arn:partition:service:region:account-id:resource-type/resource-id
            # arn:partition:service:region:account-id:resource-type:resource-id
            'aws': r'\1<account_id>\2<\3>',
            'aws2': r'\1:<resource>',
            'aws3': r'<access_key>',
            'aws4': r'<sts_token>',
            'aws5': r'<secret_key>',
            'aws6': r'<sts_access_key>',
            'aws7': r'<sg-xxxxxxxx>',
            'aws8': r'\1://<bucket>/',
            'aws9': r'<subnet-xxxxxxxx>',
            #'aws10': r'ec2-x-x-x-x.<region>\1',
            'db': r'\1<database>',
            'db2': r'\1<database_instance>',
            'db3': r'\1<schema>',
            'db4': r'\1<\2>',
            'db5': r'/user/hive/warehouse/<database>.db/<table>',
            'generic': r'\1://<file>',
            'generic2': r'\1<key>',
            'generic3': r'\1<cluster>',
            'generic4': r'\1<function>',
            'generic5': r'\1<load_balancer_name>',
            'hostname': r'<hostname>:\2',
            #'hostname2': '<aws_hostname>',
            'hostname2': r'<ip-x-x-x-x>',
            'hostname3': r'\1<hostname>',
            'hostname4': r'\\\\<hostname>',
            'hostname5': r'\1<hostname>',
            'hostname6': r'\1<hostname>',
            'domain2': '@<domain>',
            'port': ':<port>',
            'user': r'\1<user>',
            'user2': r'/\1/<user>',
            'user3': r'\1<user>',
            'user4': r'<domain>\\<user>',
            'user5': 'for user <user>',
            'user6': '<user>@',
            'user7': r'\1<user>',
            'user8': r'\1<account_id>\2<user>',
            'group': r'\1<group>',
            'group2': r'\1<group>',
            'group3': r'for group <group>',
            'group4': r'\1<group>',
            'group5': r'\1<account_id>\2<group>',
            'password': r'\1<password>',
            'password2': r'\1<user>:<password>',
            'password3': r'\1<user>\2<password>',
            'password4': r'\1<token>',
            'ip': r'<ip_x.x.x.x>/<cidr_mask>',
            'ip2': r'<ip_x.x.x.x>',
            'ip3': r'<ip-x-x-x-x>',
            'ip_prefix': r'<ip_x.x.x>.\1/<cidr_mask>',
            'ip_prefix2': r'<ip_x.x.x>.\1',
            'ip_prefix3': r'<ip-x-x-x>.\1',
            'subnet_mask': r'<subnet_x.x.x.x>',
            'kerberos': r'host/\1@<domain>',
            'kerberos2': r'host/<instance>@<domain>',
            'kerberos3': r'<user>/\1@<domain>',
            'kerberos4': r'<user>/<instance>@<domain>',
            'kerberos5': '/krb5cc_<uid>',
            #'kerberos6': r'<kerberos_principal>',
            'email': '<user>@<domain>',
            'ldap': ldap_lambda_lowercase,
            'ldap2': ldap_lambda_lowercase,
            'ldap3': ldap_lambda_lowercase,
            'proxy': r'proxy <proxy_host> port <proxy_port>',
            'proxy2': r'Connected to <proxy_host> (<proxy_ip>) port <proxy_port>',
            'proxy3': r'\1<proxy_ip>',
            'http_auth': r'$1<user>:<password>@',
            'http_auth2': r'\1\'<proxy_user>\2\3/',
            'http_auth3': r'Authorization: Basic <token>',
            'http_auth4': r'\1<token>',
            'cisco': r'username <username> password <password>',
            'cisco2': r'password <cisco_password>',
            'cisco3': r'secret <secret>',
            'cisco4': r' md5 <md5>',
            'cisco5': r' community <community>',
            'cisco6': r'\1 <auth>',
            'cisco7': r'remote-as <AS>',
            'cisco8': r'description <cisco_description>',
            'screenos': r'set admin \1 <anonymized>',
            'screenos2': r'set snmp \1 <anonymized>',
            'screenos3': r' md5 <md5>',
            'screenos4': r' key <key>',
            'screenos5': r'set nsmgmt init id <id>',
            'screenos6': r'preshare <psk> ',
            'junos': r'pre-shared-key <psk>',
            'junos2': r' home <home>',
            'network': r'username <username>',
            'network2': r'syscontact <syscontact>',
            'windows': r'<windows_SID>',
        }

    def add_options(self):
        super(Anonymize, self).add_options()
        self.add_opt('-f', '--files', dest='files', metavar='<files>',
                     help='File(s) to anonymize, non-option arguments are also counted as files. If no files are ' + \
                          'given uses standard input stream')
        self.add_opt('-a', '--all', action='store_true',
                     help='Apply all anonymizations (careful this includes --host which can be overzealous and ' + \
                          'match too many things, in which case try more targeted anonymizations below)')
        self.add_opt('-w', '--aws', action='store_true',
                     help='Apply AWS anonymizations (access/secret keys, STS tokens, ARNs, buckets, security groups)')
        self.add_opt('-b', '--db', '--database', action='store_true',
                     help='Apply database anonymizations (db name, instance name)')
        self.add_opt('-g', '--generic', action='store_true',
                     help='Apply generic anonymizations (file://, key, cluster name / id etc)')
        self.add_opt('-C', '--custom', action='store_true',
                     help='Apply custom phrase anonymization (add your Name, Company Name etc to the list of ' + \
                          'blacklisted words/phrases one per line in anonymize_custom.conf). Matching is case ' + \
                          'insensitive. Recommended to use to work around --host matching too many things')
        self.add_opt('-i', '--ip', action='store_true',
                     help='Apply IPv4 IP address and Mac address format anonymization. This and --ip-prefix below ' + \
                          'can end up matching version numbers (eg. \'HDP 2.2.4.2\' => \'HDP <ip>\'), in which ' + \
                          'case you can switch to putting your network prefix regex in anonymize_custom.conf and ' + \
                          'using just use --custom instead')
        self.add_opt('--ip-prefix', action='store_true',
                     help='Apply IPv4 IP address prefix anonymization but leave last octet to help distinguish ' + \
                          'nodes for cluster debugging (eg. \'node 172.16.100.51 failed to contact 172.16.100.52\'' + \
                          '=> \'<ip_prefix>.51 failed to contact <ip_prefix>.52\') , still applies full Mac ' + \
                          'address format anonymization')
        self.add_opt('-H', '--host', action='store_true',
                     help='Apply host, domain and fqdn format anonymization (same as -odF). This may anonymize ' + \
                          'some Java stack traces of class names also, in which case you can either try ' + \
                          '--skip-java-exceptions or avoid using --domain/--fqdn (or --host/--all which includes ' + \
                          'them), and instead use --custom and put your host/domain regex in anonymize_custom.conf')
        self.add_opt('-o', '--hostname', action='store_true',
                     help='Apply hostname format anonymization (only works on \'<host>:<port>\' otherwise this ' + \
                          'would match everything (consider using --custom and putting your hostname convention ' + \
                          'regex in anonymize_custom.conf to catch other shortname references)')
        self.add_opt('--hash-hostnames', action='store_true',
                     help='Hash hostnames / FQDNs to still be able to distinguish different nodes for cluster ' + \
                          'debugging, these are salted and truncated to be indistinguishable from temporal docker ' + \
                          'container IDs, but someone with enough computing power and time could theoretically ' + \
                          'calculate the source hostnames so don\'t put these on the public internet, it is more ' + \
                          'for private vendor tickets')
        self.add_opt('-d', '--domain', action='store_true',
                     help='Apply domain format anonymization')
        self.add_opt('-F', '--fqdn', action='store_true',
                     help='Apply FQDN format anonymization')
        self.add_opt('-P', '--port', action='store_true',
                     help='Apply port anonymization (not included in --all since you usually want to include port ' + \
                          'numbers for cluster or service debugging)')
        self.add_opt('-u', '--user', action='store_true',
                     help='Apply user anonymization (user=<user>). Auto enables --password')
        self.add_opt('-p', '--password', action='store_true',
                     help='Apply password anonymization against --password switches (can\'t catch MySQL ' + \
                          '-p<password> since it\'s too ambiguous with bunched arguments, can use --custom ' + \
                          'to work around). Also covers curl -u user:password and auto enables --http-auth')
        self.add_opt('-T', '--http-auth', action='store_true',
                     help=r'Apply HTTP auth anonymization to replace Basic Authorization tokens and' + \
                          r'http://username:password\@ => ' + \
                          r'http://<user>:<password>\@. Also works with https://')
        self.add_opt('-K', '--kerberos', action='store_true',
                     help=r'Apply Kerberos anonymizations eg. <primary>@<realm>, <primary>/<instance>@<realm> ' + \
                          '(where <realm> must match a valid domain name - otherwise use --custom and populate ' + \
                          r'anonymize_custom.conf). Hadoop principals preserve the generic _HOST placeholder eg. ' + \
                          '<user>/_HOST@<realm> (if wanting to retain full prefix eg. NN/_HOST then use ' + \
                          '--domain instead of --kerberos). --kerberos auto-enables --email, --domain and --fqdn')
        self.add_opt('-L', '--ldap', action='store_true',
                     help='Apply LDAP anonymization ' + \
                          '(~100 attribs eg. CN, DN, OU, UID, sAMAccountName, member, memberOf...)')
        self.add_opt('-E', '--email', action='store_true',
                     help='Apply email format anonymization')
        #self.add_opt('-x', '--proxy', action='store_true',
        #             help='Apply anonymization to remove proxy host, user etc (eg. from curl -iv output). You ' + \
        #                  'should probably also apply --ip and --host if using this. Auto enables --http-auth')
        self.add_opt('-N', '--network', action='store_true',
                     help='Apply all network anonymization, whether Cisco, ScreenOS, JunOS for secrets, auth, ' + \
                          'usernames, passwords, md5s, PSKs, AS, SNMP community strings etc.')
        self.add_opt('-c', '--cisco', action='store_true',
                     help='Apply Cisco IOS/IOS-XR/NX-OS configuration format anonymization')
        self.add_opt('-s', '--screenos', action='store_true',
                     help='Apply Juniper ScreenOS configuration format anonymization')
        self.add_opt('-j', '--junos', action='store_true',
                     help='Apply Juniper JunOS configuration format anonymization (limited, please raise a ticket ' + \
                          'for extra matches to be added)')
        self.add_opt('-W', '--windows', action='store_true',
                     help='Windows Sids (UNC path hostnames are already stripped by --hostname and ' + \
                          'DOMAIN\\user components are already stripped by --user)')
        self.add_opt('-r', '--strip-cr', action='store_true',
                     help='Strip carriage returns (\'\\r\') from end of lines leaving only newlines (\'\\n\')')
        self.add_opt('--skip-java-exceptions', action='store_true',
                     help='Skip lines with Java Exceptions from generic host/domain/fqdn anonymization to prevent ' + \
                          'anonymization java classes needed for debugging stack traces. This is slightly risky ' + \
                          'as it may potentially miss hostnames/fqdns if colocated on the same lines. Should ' + \
                          'populate anonymize_custom.conf with your domain to remove those instances. After ' + \
                          'tighter improvements around matching only IANA TLDs this should be less needed now')
        self.add_opt('--skip-python-tracebacks', action='store_true',
                     help='Skip lines with Python Tracebacks, similar to --skip-java-exceptions')
        self.add_opt('-e', '--skip-exceptions', action='store_true',
                     help='Skip both Java exceptions and Python tracebacks (recommended)')

    def process_options(self):
        super(Anonymize, self).process_options()
        files = self.get_opt('files')
        if files:
            self.file_list = set(files.split(','))
        self.file_list = self.file_list.union(self.args)
        self._validate_filenames()
        if self.get_opt('all'):
            for _ in self.anonymizations:
                if _ == 'ip_prefix':
                    continue
                self.anonymizations[_] = True
            if self.get_opt('ip_prefix'):
                self.anonymizations['ip_prefix'] = True
                self.anonymizations['ip'] = False
        else:
            for _ in self.anonymizations:
                # pylint: disable=no-else-continue
                if _ in ('subnet_mask', 'mac', 'group'):
                    continue
                elif _ == 'database':
                    self.anonymizations['db'] = True
                else:
                    self.anonymizations[_] = self.get_opt(_)
                log.debug('anonymization enabled %s = %s', _, bool(self.anonymizations[_]))
        self._process_options_host()
        self._process_options_network()
        self._process_options_exceptions()
        if not self._is_anonymization_selected():
            self.usage('must specify one or more anonymization types to apply')
        if self.anonymizations['ip'] and self.anonymizations['ip_prefix']:
            self.usage('cannot specify both --ip and --ip-prefix, they are mutually exclusive behaviours')
        if self.anonymizations['user']:
            self.anonymizations['group'] = True

    def _validate_filenames(self):
        for filename in self.file_list:
            if filename == '-':
                log_option('file', '<STDIN>')
            else:
                validate_file(filename)
        # use stdin
        if not self.file_list:
            self.file_list.add('-')

    def _process_options_host(self):
        if self.anonymizations['ip'] or \
           self.anonymizations['ip_prefix']:
            self.anonymizations['subnet_mask'] = True
            self.anonymizations['mac'] = True
        host = self.get_opt('host')
        if self.get_opt('hash_hostnames'):
            host = True
            self.hash_salt = md5(open(__file__).read()).hexdigest()
            # will end up double hashing FQDNs that are already hashed to 12 char alnum
            self.replacements['hostname'] = lambda match: r'{hostname}:{port}'\
                                            .format(hostname=self.hash_host(match.group(1)), port=match.group(2))
            self.replacements['hostname2'] = lambda match: r'{ip}'.format(ip=self.hash_host(match.group(1)))
            self.replacements['hostname3'] = lambda match: r'{protocol}{hostname}'\
                                             .format(protocol=match.group(1),
                                                     hostname=self.hash_host(match.group(2))
                                                    )
            self.replacements['hostname4'] = lambda match: r'\\{hostname}'\
                                             .format(hostname=self.hash_host(match.group(1)))
            self.replacements['hostname5'] = lambda match: r'{switch}{hostname}'\
                                             .format(switch=match.group(1), hostname=self.hash_host(match.group(2)))
            self.replacements['fqdn'] = lambda match: self.hash_host(match.group(1))
        if host:
            for _ in ('hostname', 'fqdn', 'domain'):
                self.anonymizations[_] = True
        if self.anonymizations['kerberos']:
            self.anonymizations['email'] = True
            self.anonymizations['domain'] = True
            self.anonymizations['fqdn'] = True
        #if self.anonymizations['proxy']:
        #    self.anonymizations['http_auth'] = True

    def _process_options_network(self):
        if self.anonymizations['network']:
            for _ in ('cisco', 'screenos', 'junos'):
                self.anonymizations[_] = True
        for _ in ('cisco', 'screenos', 'junos'):
            if self.anonymizations[_]:
                self.anonymizations['network'] = True

    def _process_options_exceptions(self):
        if self.get_opt('skip_exceptions'):
            for _ in self.exceptions:
                self.exceptions[_] = True
        else:
            for _ in self.exceptions:
                self.exceptions[_] = self.get_opt('skip_' + _)

    def hash_host(self, host):
        # hash entire hostname and do not preserve .<domain> suffix
        # to avoid being able to differentiate from temporal Docker container IDs
        #parts = host.split('.', 2)
        #shortname = parts[0]
        #domain = None
        #if len(parts) > 1:
        #    domain = parts[1]
        #hashed_hostname = md5(self.hash_salt + shortname).hexdigest()[:12]
        #if domain:
        #    hashed_hostname += '.' + '<domain>'
        hashed_hostname = md5(self.hash_salt + host).hexdigest()[:12]
        return hashed_hostname

    def _is_anonymization_selected(self):
        for _ in self.anonymizations:
            if self.anonymizations[_]:
                return True
        return False

    @staticmethod
    def load_file(filename, boundary=False):
        log.info('loading custom regex patterns from %s', filename)
        regex_list = []
        re_ending_pipe = re.compile(r'\|\s*$')
        re_leading_space = re.compile(r'^\s*')
        with open(filename) as filehandle:
            for line in filehandle:
                line = line.rstrip('\n')
                line = line.rstrip('\r')
                line = line.split('#')[0]
                line = re_ending_pipe.sub('', line)
                line = re_leading_space.sub('', line)
                if not line:
                    continue
                if not isRegex(line):
                    log.warning('ignoring invalid regex from %s: %s', os.path.basename(filename), line)
                    continue
                if boundary:
                    line = r'(?:(?<=\b)|(?<=[^A-Za-z]))' + line + r'(?=\b|[^A-Za-z])'
                regex_list.append(line)
        raw = '|'.join(regex_list)
        #log.debug('custom_raw: %s', raw)
        regex_list = [re.compile(_, re.I) for _ in regex_list]
        return (regex_list, raw)

    def run(self):
        (self.custom_anonymizations, _) = self.load_file(self.custom_anonymization_file, boundary=True)
        (self.custom_ignores, self.custom_ignores_raw) = self.load_file(self.custom_ignore_file)
        self.prepare_regex()
        for filename in self.file_list:
            self.process_file(filename)

    # allow to easily switch pre-compilation on/off for testing
    # testing shows on a moderate sized file that it is a couple secs quicker to use pre-compiled regex
    def compile(self, name, regex):
        self.regex[name] = re.compile(regex, re.I)
        #self.regex[name] = regex

    def prepare_regex(self):
        self.compile('hostname',
                     r'(?<!\w\]\s)' + \
                     r'(?<!\.)' + \
                     # ignore Java methods such as SomeClass$method:20
                     r'(?<!\$)' + \
                     # ignore Java stack traces eg. at SomeClass(Thread.java;789)
                     r'(?!\(\w+\.java:\d+\))' + \
                     # don't match 2018-01-01T00:00:00 => 2018-01-<hostname>:00:00
                     r'(?!\d+T\d+:\d+)' + \
                     r'(?!\d+[^A-Za-z0-9]|' + \
                     self.custom_ignores_raw + ')' + \
                     '(' + hostname_regex + ')' + \
                     self.negative_host_lookbehind + r':(\d{1,5}(?!\.?\w))',
                    )
        self.compile('domain',
                     # don't match java -some.net.property
                     #r'(?<!-)' + \
                     r'(?!' + self.custom_ignores_raw + ')' + \
                     domain_regex_strict + \
                     # don't match java -Dsome.net.property=
                     r'(?!=)' + \
                     r'(?!\.[A-Za-z])(\b|$)' + \
                     # ignore Java stack traces eg. at SomeClass(Thread.java;789)
                     r'(?!\(\w+\.java:\d+\))' + \
                     self.negative_host_lookbehind
                    )
        self.compile('fqdn',
                     # don't match java -some.net.property
                     #r'(?<!-)' + \
                     r'(?!' + self.custom_ignores_raw + ')' + \
                     '(' + fqdn_regex + ')' + \
                     # don't match java -Dsome.net.property=
                     r'(?!=)' + \
                     r'(?!\.[A-Za-z])(\b|$)' + \
                     # ignore Java stack traces eg. at SomeClass(Thread.java;789)
                     r'(?!\(\w+\.java:\d+\))' + \
                     self.negative_host_lookbehind
                    )
        re_regex_ending = re.compile('_regex$')
        # auto-populate any *_regex to self.regex[name] = name_regex
        for _ in globals():
            if re_regex_ending.search(_) and \
                    re_regex_ending.sub('', _) not in self.regex:
                self.regex[re.sub('_regex$', '', _)] = globals()[_]
        for _ in self.regex:
            if isStr(self.regex[_]):
                self.compile(_, self.regex[_])

    def process_file(self, filename):
        anonymize = self.anonymize
        # will be caught be generic handler and exit if the filename isn't readable,
        # don't want to pass on this as our output would be incomplete - better to fail in a noticeable way
        lineno = 0
        try:
            if filename == '-':
                for line in sys.stdin:
                    lineno += 1
                    line = anonymize(line)
                    print(line, end='')
            else:
                with open(filename) as filehandle:
                    for line in filehandle:
                        lineno += 1
                        line = anonymize(line)
                        print(line, end='')
        except AssertionError as _:
            raise AssertionError('{} line {}: {}'.format(filename, lineno, _))

    def anonymize(self, line):
        #log.debug('anonymize: line: %s', line)
        match = self.re_line_ending.search(line)
        line_ending = ''
        if match:
            line_ending = match.group(1)
        if self.strip_cr:
            line_ending = '\n'
        if not isPythonMinVersion(3):
            line = line.decode('utf-8').encode('ascii', errors='replace')
        line = strip_ansi_escape_codes(line)
        line = self.re_line_ending.sub('', line)
        for _ in self.anonymizations:
            if not self.anonymizations[_]:
                continue
            method = None
            try:
                #log.debug('checking for anonymize_%s', _)
                method = getattr(self, 'anonymize_' + _)
            except AttributeError:
                #log.debug('anonymize_%s not found', _)
                pass
            if method:
                #log.debug('found anonymize_%s: %s', _, method)
                line = method(line)
            else:
                line = self.anonymize_dynamic(_, line)
            if line is None:
                if method:
                    raise AssertionError('anonymize_{} returned None'.format(_))
                raise AssertionError('anonymize_dynamic({}, line)'.format(_))
        line += line_ending
        return line

    def anonymize_dynamic(self, name, line):
        #log.debug('anonymize_dynamic(%s, %s)', name, line)
        if not isStr(line):
            raise AssertionError('anonymize_dynamic: passed in non-string line: {}'.format(line))
        line = self.dynamic_replace(name, line)
        for i in range(2, 101):
            name2 = '{}{}'.format(name, i)
            if name2 in self.regex:
                line = self.dynamic_replace(name2, line)
            else:
                break
        return line

    def dynamic_replace(self, name, line):
        #log.debug('dynamic_replace: %s, %s', name, line)
        replacement = self.replacements.get(name, '<{}>'.format(name))
        #log.debug('%s replacement = %s', name, replacement)
        line = self.regex[name].sub(replacement, line)
        #line = re.sub(self.regex[name], replacement, line)
        log.debug('dynamic_replace: %s => %s', name, line)
        return line

    def anonymize_custom(self, line):
        i = 0
        for regex in self.custom_anonymizations:
            i += 1
            line = regex.sub(r'<custom>', line)
            #line = re.sub(regex, r'\1<custom>\2', line)
            log.debug('anonymize_custom: %s => %s', i, line)
        return line

    @staticmethod
    def isGenericPythonLogLine(line):  # pylint: disable=invalid-name
        if re.search(r'\s' + filename_regex + r'.py:\d+ - loglevel=[\w\.]+\s*$', line, re.I):
            return True
        return False

    def skip_exceptions(self, line):
        if self.exceptions['java_exceptions'] and isJavaException(line):
            return True
        if self.exceptions['python_tracebacks'] and (isPythonTraceback(line) or self.isGenericPythonLogLine(line)):
            return True
        return False

    def anonymize_hostname(self, line):
        if self.skip_exceptions(line):
            return line
        line = self.anonymize_dynamic('hostname', line)
        return line

    def anonymize_domain(self, line):
        if self.skip_exceptions(line):
            return line
        line = self.anonymize_dynamic('domain', line)
        return line

    def anonymize_fqdn(self, line):
        if self.skip_exceptions(line):
            return line
        line = self.anonymize_dynamic('fqdn', line)
        return line


if __name__ == '__main__':
    Anonymize().main()

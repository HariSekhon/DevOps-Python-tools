#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-08-08 19:02:02 +0100 (Wed, 08 Aug 2018)
#  ported from Perl version from Perl Tools repo (https://github.com/harisekhon/tools)
#  Date: 2013-07-18 21:17:41 +0100 (Thu, 18 Jul 2013)
#
#  https://github.com/harisekhon/pytools
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

Works like a standard unix filter program, taking input from standard input or file(s) given as arguments and
prints the modified output to standard output (to redirect to a new file or copy buffer).

Create a list of phrases to anonymize from config by placing them in anonymize_custom.conf in the same directory
as this program, one PCRE format regex per line, blank lines and lines prefixed with # are ignored.

Ignore phrases are in a similar file anonymize_ignore.conf, also adjacent to this program.

Based on Perl Anonymize.pl from https://github.com/harisekhon/tools

My Perl version is incredibly faster than this Python version at this time

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
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
        isRegex, \
        isStr, \
        log, \
        log_option, \
        validate_file
    # used dynamically
    # pylint: disable=unused-import
    from harisekhon.utils import \
        domain_regex, \
        domain_regex_strict, \
        email_regex, \
        filename_regex, \
        fqdn_regex, \
        host_regex, \
        hostname_regex, \
        ip_prefix_regex, \
        ip_regex, \
        mac_regex, \
        subnet_mask_regex, \
        user_regex
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2'


class Anonymize(CLI):

    def __init__(self):
        # Python 2.x
        super(Anonymize, self).__init__()
        # Python 3.x
        # super().__init__()
        self.custom_anonymization_file = os.path.join(srcdir, 'anonymize_custom.conf')
        self.custom_ignore_file = os.path.join(srcdir, 'anonymize_ignore.conf')
        self.custom_anonymizations = set()
        self.custom_ignores = set()
        self.custom_ignores_raw = ''
        self.file_list = set()
        self.re_line_ending = re.compile(r'(\r?\n)$')
        self.strip_cr = False
        # order of iteration of application matters because we must do more specific matches before less specific ones
        self.anonymizations = OrderedDict([
            ('ip', False),
            ('ip_prefix', False),
            ('subnet_mask', False),
            ('mac', False),
            ('kerberos', False),
            ('email', False),
            ('password', False),
            ('user', False),
            ('proxy', False),
            ('http_auth', False),
            ('cisco', False),
            ('screenos', False),
            ('junos', False),
            ('network', False),
            ('fqdn', False),
            ('domain', False),
            ('hostname', False),
            ('custom', False),
        ])
        self.exceptions = {
            'java_exceptions': False,
            'python_tracebacks': False,
        }
        self.negative_host_lookbehind = r'(?<!\.java)(?<!\.py)(?<!\sid)'
        # don't use this simpler one as we want to catch everything inside quotes eg. 'my secret'
        #password_regex = r'\S+'
        password_regex = r'(?:\'[^\']+\'|"[^"]+"|\S+)'
        self.regex = {
            'hostname2': r'\b(?:ip-10-\d+-\d+-\d+|' + \
                         r'ip-172-1[6-9]-\d+-\d+|' + \
                         r'ip-172-2[0-9]-\d+-\d+|' + \
                         r'ip-172-3[0-1]-\d+-\d+|' +
                         r'ip-192-168-\d+-\d+)\b(?!-\d)',
            'user': r'(-user[=\s]+)\S+',
            'user2': r'/home/\S+',
            # openssl uses -passin switch
            'password': r'(\b(?:password|passin)(?:=|\s+)){pw}'.format(pw=password_regex),
            'password2': r'(\bcurl\s.*?-[A-Za-tv-z]*u(?:=|\s+)?)[^:\s]+:{pw}'.format(pw=password_regex),
            'ip_prefix': r'{}(?!\.\d+\.\d+)'.format(ip_prefix_regex),
            # network device format Mac address
            'mac2': r'\b(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}\b',
            'kerberos': user_regex + '/_HOST@' + domain_regex,
            'kerberos2': r'\b' + user_regex + r'(?:\/' + hostname_regex + r')?@' + domain_regex + r'\b/',
            # network device format mac address
            'mac2': r'\b(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}\b',
            'proxy': 'proxy ' + host_regex + r'port \d+',
            'proxy2': 'Trying' + ip_regex,
            'proxy3': 'Connected to ' + host_regex + r'\($ip_regex\) port \d+',
            'proxy4': r'(Via:\s[^\s]+\s)' + ip_regex + '.*',
            'http_auth': r'(https?:\/\/)[^:]+:[^\@]*\@',
            'http_auth2': r'(Proxy auth using \w+ with user )([\'"]).+([\'"])',
            'cisco': r'username .+ (?:password|secret) .*?$',
            'cisco2': r'password .*?$',
            'cisco3': r'\ssecret\s.*?$',
            'cisco4': r'\smd5\s+.*?$',
            'cisco5': r'\scommunity\s+.*$',
            'cisco6': r'(standby\s+\d+\s+authentication).*',
            'cisco7': r'\sremote-as\s\d+',
            'cisco8': r'\sdescription\s.*$',
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
        }
        # auto-populate any *_regex to self.regex[name] = name_regex
        for _ in globals():
            if re.sub('_regex$', '', _) not in self.regex and re.search('_regex$', _):
                self.regex[re.sub('_regex$', '', _)] = globals()[_]
        for _ in self.regex:
            self.regex[_] = re.compile(self.regex[_])
        # will auto-infer replacements to not have to be explicit, use this only for override mappings
        self.replacements = {
            'hostname': r'<hostname>:\1',
            'hostname2': '<aws_hostname>',
            'user': r'\1<user>',
            'user2': '/home/<user>',
            'password': r'\1<password>',
            'password2': r'\1<user>:<password>',
            'ip_prefix': r'<ip_prefix>.',
            'kerberos': r'<kerberos_primary>\/_HOST@<kerberos_realm>',
            'kerberos2': r'<kerberos_principal>',
            'proxy': r'proxy <proxy_host> port <proxy_port>',
            'proxy2': r'Trying <proxy_ip>',
            'proxy3': r'Connected to <proxy_host> (<proxy_ip>) port <proxy_port>',
            'http_auth': r'$1<user>:<password>@',
            'http_auth2': r'\1\'<proxy_user>\2\3/',
            'proxy4': r'\1<proxy_ip>',
            'cisco': r'username <username> password <password>',
            'cisco2': r'password <password>',
            'cisco3': r'secret <secret>',
            'cisco4': r' md5 <md5>',
            'cisco5': r' community <community>',
            'cisco6': r'\1 <auth>',
            'cisco7': r'remote-as <AS>',
            'cisco8': r'description <description>',
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
        }

    def add_options(self):
        super(Anonymize, self).add_options()
        self.add_opt('-f', '--files', dest='files', metavar='<files>',
                     help='File(s) to anonymize, non-option arguments are also counted as files. If no files are ' + \
                          'given uses standard input stream')
        self.add_opt('-a', '--all', action='store_true',
                     help='Apply all anonymizations (careful this includes --host which can be overzealous and ' + \
                          'match too many things, in which case try more targeted anonymizations below)')
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
        self.add_opt('-d', '--domain', action='store_true',
                     help='Apply domain format anonymization')
        self.add_opt('-F', '--fqdn', action='store_true',
                     help='Apply fqdn format anonymization')
        self.add_opt('-P', '--port', action='store_true',
                     help='Apply port anonymization (not included in --all since you usually want to include port ' + \
                          'numbers for cluster or service debugging)')
        self.add_opt('-u', '--user', action='store_true',
                     help='Apply user anonymization (user=<user>). Auto enables --password')
        self.add_opt('-p', '--password', action='store_true',
                     help='Apply password anonymization against --password switches (can\'t catch MySQL ' + \
                          '-p<password> since it\'s too ambiguous with bunched arguments, can use --custom ' + \
                          'to work around). Also covers curl -u user:password')
        self.add_opt('-T', '--http-auth', action='store_true',
                     help=r'Apply HTTP auth anonymization to replace http://username:password\@ => ' + \
                          r'http://<user>:<password>\@. Also works with https://')
        self.add_opt('-k', '--kerberos', action='store_true',
                     help=r'Kerberos 5 principals in the form <primary>@<realm> or <primary>/<instance>@<realm> ' + \
                          '(where <realm> must match a valid domain name - otherwise use --custom and populate ' + \
                          r'anonymize_custom.conf). These kerberos principals are anonymizebed to ' + \
                          '<kerberos_principal>. There is a special exemption for Hadoop Kerberos principals such ' + \
                          'as NN/_HOST@<realm> which preserves the literal \'_HOST\' instance since that\'s ' + \
                          'useful to know for debugging, the principal and realm will still be anonymizebed in ' + \
                          'those cases (if wanting to retain NN/_HOST then use --domain instead of --kerberos). ' + \
                          'This is applied before --email in order to not prevent the email replacement leaving ' + \
                          r'this as user/host\@realm to user/<email_regex>, which would have exposed \'user\'')
        self.add_opt('-E', '--email', action='store_true',
                     help='Apply email format anonymization')
        self.add_opt('-x', '--proxy', action='store_true',
                     help='Apply anonymization to remove proxy host, user etc (eg. from curl -iv output). You ' + \
                          'should probably also apply --ip and --host if using this. Auto enables --http-auth')
        self.add_opt('-n', '--network', action='store_true',
                     help='Apply all network anonymization, whether Cisco, ScreenOS, JunOS for secrets, auth, ' + \
                          'usernames, passwords, md5s, PSKs, AS, SNMP etc.')
        self.add_opt('-c', '--cisco', action='store_true',
                     help='Apply Cisco IOS/IOS-XR/NX-OS configuration format anonymization')
        self.add_opt('-s', '--screenos', action='store_true',
                     help='Apply Juniper ScreenOS configuration format anonymization')
        self.add_opt('-j', '--junos', action='store_true',
                     help='Apply Juniper JunOS configuration format anonymization (limited, please raise a ticket ' + \
                          'for extra matches to be added)')
        self.add_opt('-m', '--custom', action='store_true',
                     help='Apply custom phrase anonymization (add your Name, Company Name etc to the list of ' + \
                          'blacklisted words/phrases one per line in anonymize_custom.conf). Matching is case ' + \
                          'insensitive. Recommended to use to work around --host matching too many things')
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
        file_list = self.file_list
        if self.args:
            for arg in self.args:
                file_list.add(arg)
        for filename in file_list:
            if filename == '-':
                log_option('file', '<STDIN>')
            else:
                validate_file(filename)
        # use stdin
        if not file_list:
            file_list.add('-')
        if self.get_opt('all'):
            for _ in self.anonymizations:
                if _ == 'ip_prefix':
                    #self.anonymizations[_] = False
                    continue
                self.anonymizations[_] = True
        else:
            for _ in self.anonymizations:
                if _ in ('subnet_mask', 'mac'):
                    continue
                self.anonymizations[_] = self.get_opt(_)
        ######
        if self.anonymizations['ip'] or self.anonymizations['ip_prefix']:
            self.anonymizations['subnet_mask'] = True
            self.anonymizations['mac'] = True
        if self.get_opt('host'):
            for _ in ('hostname', 'fqdn', 'domain'):
                self.anonymizations[_] = True
        if self.anonymizations['proxy']:
            self.anonymizations['http_auth'] = True
        if self.anonymizations['network']:
            for _ in ('cisco', 'screenos', 'junos'):
                self.anonymizations[_] = True
        for _ in ('cisco', 'screenos', 'junos'):
            if self.anonymizations[_]:
                self.anonymizations['network'] = True
        #######
        if not self.is_anonymization_selected():
            self.usage('must specify one or more anonymization types to apply')
        if self.anonymizations['ip'] and self.anonymizations['ip_prefix']:
            self.usage('cannot specify both --ip and --ip-prefix, they are mutually exclusive behaviours')
        if self.get_opt('skip_exceptions'):
            for _ in self.exceptions:
                self.exceptions[_] = True
        else:
            for _ in self.exceptions:
                self.exceptions[_] = self.get_opt('skip_' + _)

    def is_anonymization_selected(self):
        for _ in self.anonymizations:
            if self.anonymizations[_]:
                return True
        return False

    @staticmethod
    def load_file(filename, boundary=False):
        log.info('loading custom regex patterns from %s', filename)
        regex = set()
        raw = ''
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
                    line = r'(\b|[^A-Za-z])' + line + r'(\b|[^A-Za-z])'
                regex.add(re.compile(line, re.I))
                raw += line + '|'
        raw = raw.rstrip('|')
        #log.debug('custom_raw: %s', raw)
        return (regex, raw)

    def run(self):
        (self.custom_anonymizations, _) = self.load_file(self.custom_anonymization_file, boundary=True)
        (self.custom_ignores, self.custom_ignores_raw) = self.load_file(self.custom_ignore_file)
        self.prepare_regex()
        for filename in self.file_list:
            self.process_file(filename)

    def prepare_regex(self):
        self.regex['hostname'] = re.compile(
            r'(?<!\w\]\s)' + \
            r'(?<!\.)' + \
            r'(?!\d+[^A-Za-z0-9]|' + \
            self.custom_ignores_raw + ')' + \
            hostname_regex + \
            self.negative_host_lookbehind + r':(\d{1,5}(?:[^A-Za-z]|$))',
            re.I)
        self.regex['domain'] = re.compile(
            r'(?!' + self.custom_ignores_raw + ')' + \
            domain_regex_strict + \
            r'(?!\.[A-Za-z])(\b|$)' + \
            self.negative_host_lookbehind, re.I)
        self.regex['fqdn'] = re.compile(
            r'(?!' + self.custom_ignores_raw + ')' + \
            fqdn_regex + \
            r'(?!\.[A-Za-z])(\b|$)' + \
            self.negative_host_lookbehind, re.I)
        self.regex['ip'] = re.compile(r'(?<!\d.)' + ip_regex + r'(?![^:]\d+)')
        self.regex['subnet_mask'] = re.compile(r'(?<!\d.)' + subnet_mask_regex + r'(?![^:]\d+)')
        self.regex['ip_prefix'] = re.compile(r'(?<!\d.)' + ip_prefix_regex + r'(?!\.\d+\.\d+)')

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
                    print(line)
            else:
                with open(filename) as filehandle:
                    for line in filehandle:
                        lineno += 1
                        line = anonymize(line)
                        print(line)
        except AssertionError as _:
            raise AssertionError('{} line {}: {}'.format(filename, lineno, _))

    def anonymize(self, line):
        #log.debug('anonymize: line: %s', line)
        match = self.re_line_ending.search(line)
        line_ending = ""
        if match:
            line_ending = match.group(1)
        if self.strip_cr:
            line_ending = "\n"
        line = self.re_line_ending.sub("", line)
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
                    raise AssertionError('anonymize_{} returned None', _)
                else:
                    raise AssertionError('anonymize_dynamic({}, line)', _)
        line += line_ending
        return line

    def anonymize_dynamic(self, name, line):
        #log.debug('anonymize_dynamic(%s, %s)', name, line)
        if not isStr(line):
            raise AssertionError('anonymize_dynamic: passed in non-string line: %s', line)
        line = self.dynamic_replace(name, line)
        for i in range(2, 101):
            name2 = '{}{}'.format(name, i)
            if name2 in self.regex:
                line = self.dynamic_replace(name2, line)
            else:
                break
        return line

    def dynamic_replace(self, name, line):
        replacement = self.replacements.get(name, '<{}>'.format(name))
        #log.debug('%s replacement = %s', name, replacement)
        line = self.regex[name].sub(replacement, line)
        return line

    def anonymize_custom(self, line):
        for regex in self.custom_anonymizations:
            line = regex.sub(r'\1<custom_anonymized>\2', line)
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

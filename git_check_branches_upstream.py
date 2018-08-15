#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-07-21 16:19:19 +0100 (Thu, 21 Jul 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to check Git branches have their upstream origin branch set consistently and auto-fix if necessary

Mainly written for my https://github.com/harisekhon/Dockerfiles repo
which has over 100 branches which get merged, pulled and pushed around

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import re
import sys
import traceback
import git
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, find_git_root, log, log_option, uniq_list_ordered, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.4'


class GitCheckBranchesUpstream(CLI):

    def __init__(self):
        # Python 2.x
        super(GitCheckBranchesUpstream, self).__init__()
        # Python 3.x
        # super().__init__()
        self.status = "OK"
        self.origin = None
        self.branch_prefix = None
        self.timeout_default = 86400
        self.verbose_default = 2

    def add_options(self):
        self.add_opt('-b', '--branch-prefix', help='Branch prefix regex to check')
        self.add_opt('-o', '--origin', help='Origin repo (default: origin)', default='origin')
        self.add_opt('-f', '--fix', action='store_true',
                     help='Set any branches without upstream to corresponding origin/<branch>')
        self.add_opt('-F', '--force-fix', action='store_true',
                     help='Override all branches\' upstreams to track corresponding origin/<branch>')

    def run(self):
        if not self.args:
            self.usage('no git directory args given')
        self.origin = self.get_opt('origin')
        args = uniq_list_ordered(self.args)
        self.branch_prefix = self.get_opt('branch_prefix')
        if self.branch_prefix is not None:
            validate_regex(self.branch_prefix, 'branch prefix')
            self.branch_prefix = re.compile(self.branch_prefix)
        for arg in args:
            if not os.path.exists(arg):
                print("'%s' not found" % arg)
                sys.exit(ERRORS['WARNING'])
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', arg)
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for arg in args:
            self.check_git_branches_upstream(arg)
        if self.status == "OK":
            log.info('SUCCESS - All Git branches are tracking the expected upstream origin branches')
        else:
            log.critical('FAILED')
            sys.exit(ERRORS['CRITICAL'])

    def check_git_branches_upstream(self, target):
        target = os.path.abspath(target)
        gitroot = find_git_root(target)
        if gitroot is None:
            die('Failed to find git root for target {0}'.format(target))
        log.debug("finding branches for target '{0}'".format(target))
        repo = git.Repo(gitroot)
        branches = repo.branches
        if self.branch_prefix is not None:
            log.debug('restricting to branches matching branch prefix')
            branches = [x for x in branches if self.branch_prefix.match(str(x))]
            if not branches:
                log.error("No branches matching '%s' for target '%s'", self.get_opt('branch_prefix'), target)
                self.status = 'NO BRANCHES'
        #if log.isEnabledFor(logging.DEBUG):
        #log.debug('\n\nbranches for target %s:\n\n%s\n', target, '\n'.join(list(branches)))
        for branch in branches:
            expected = '{0}/{1}'.format(self.origin, branch)
            # have to str() this as it returns an object that will fail equality match otherwise
            tracking_branch = str(branch.tracking_branch())
            if tracking_branch == expected:
                log.info("OK: repo '{0}' branch '{1}' is tracking '{2}'"
                         .format(gitroot, branch, tracking_branch))
            elif self.get_opt('fix') and tracking_branch == 'None':
                log.warn("WARN: setting repo '{0}' unconfigured branch '{1}' to track '{2}'"
                         .format(gitroot, branch, expected))
                #print(list(repo.remotes.origin.refs))
                branch.set_tracking_branch(git.refs.remote.RemoteReference(repo, 'refs/remotes/' + expected))
            elif self.get_opt('force_fix'):
                log.warn("WARN: forcibly resetting repo '{0}' branch '{1}' to track '{2}'"
                         .format(gitroot, branch, expected))
                branch.set_tracking_branch(git.refs.remote.RemoteReference(repo, 'refs/remotes/' + expected))
            else:
                self.status = "ERROR"
                log.error("BAD: branch '{0}' is tracking '{1}' (expected '{2}')"
                          .format(branch, tracking_branch, expected))


if __name__ == '__main__':
    GitCheckBranchesUpstream().main()

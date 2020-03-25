#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-20 20:24:12 +0100 (Fri, 20 May 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

r"""

Tool to validate Git branches are aligned with any Dockerfiles in that revision which correspond with the brancVh prefix

Recurses any given directories to find all Dockerfiles and checks their ARG *_VERSION line in each branch
to ensure they're both aligned.

This requires the git branching and Dockerfile ARG to be aligned in such as way that 'ARG NAME_VERSION=<version>'
corresponds to Git branch 'NAME-<version>' where NAME matches regex '\w+' and <version> is in the form 'x.y[.z]' where
if git branch is at least a prefix of the Dockerfiles ARG version (eg. solr-4 matches ARG SOLR_VERSION=4 and ARG
SOLR_VERSION=4.10).

Additionally, git branches of NAME-dev-<version> are stripped of '-dev' and assumed to still use ARG NAME_VERSION, and
the parent directory name for the Dockerfile must match the branch base without the version (but including the -dev
part) in order to disambiguate between things like SOLRCLOUD_VERSION for either solrcloud/Dockerfile or
solrcloud-dev/Dockerfile.

Beware this will attempt to do a git checkout of all branches and test containing Dockerfiles under given paths in each
branch revision. If the git checkout is 'dirty' (ie has uncommitted changes) it will prevent checking out the branch,
the program will detect this and exit, leaving you to decide what to do. In normal circumstances it will return to the
original branch/branch checkout when complete.

Prematurely terminating this program can leave the git checkout in an inconsistent state, although all catchable
exceptions are caught to return to original state. If you end up in an inconsistent state just git reset and do a
manual checkout back to master.

Recommended to run this on a non-working git checkout to make it easy to reset state and avoid dirty git checkout
issues eg. run inside your CI system or a secondary git clone location.

Originally this worked on a file-by-file basis which is better when recursing directories across git submodules, but
was the least efficient way of doing it so I've rewritten it to do a single pass of all branches and check all
Dockerfiles in given directories, hence it's more efficient to give this program the directory containing the
Dockerfiles than each individual Dockerfile which would result in a similar behaviour to the original, multiplying each
Dockerfile by the number of branches and doing that many checkouts.

It is more efficient to give a directory tree of Dockerfiles than individual Dockerfiles... but the caveat is that they
must all be contained in the same Git repo (not crossing git submodule boundaries etc, otherwise you must do a
'find -exec' using this program instead).

There are a couple extra conditions now too - instead of checking ARG {NAME}_VERSION where {NAME} matches branch base,
this turns out to be too restrictive for branches with multiple versions like kafka-2.10-0.9 so this program now
expects that ARG {NAME}_VERSION is in the same order as the versions of the branch name, ie SCALA_VERSION comes before
KAFKA_VERSION to match the branch's version order.

This is one of the my less generic tools in the public domain. It requires your use of git branches matches your use of
Dockerfile ARG. You're welcome to modify it to suit your needs or make it more generic (in which case please
re-submit improvements in the form of GitHub pull requests).

This was primarily written to test the Dockerfiles repository at https://github.com/HariSekhon/Dockerfiles

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import logging
import os
import re
import sys
import traceback
import git
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log, log_option
    from harisekhon.utils import find_git_root, uniq_list_ordered, isVersion, validate_regex, version_regex
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.7.3'


class DockerfileGitBranchCheckTool(CLI):

    def __init__(self):
        # Python 2.x
        super(DockerfileGitBranchCheckTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.failed = False
                                       # ARG ZOOKEEPER_VERSION=3.4.8
        self.arg_regex = re.compile(r'^\s*ARG\s+([\w_]+_VERSION)=([\w\.]+)\s*')
        self.jdk_regex = re.compile(r'.*((?:jdk|jre)\d+).*')
        self.branch_prefix = None
        self.branch_regex = re.compile(r'^([\w-]+?)-?({version_regex})(?:-((?:[A-Za-z]+)?-?{version_regex}))?$'
                                       .format(version_regex=version_regex))
        self.timeout_default = 86400
        self.valid_git_branches_msg = None
        self.invalid_git_branches_msg = None
        self.verbose_default = 2
        self.dockerfiles_checked = set()
        self.dockerfiles_failed = 0
        self.branches_checked = 0
        self.branches_dockerfile_checked = set()
        self.branches = None
        self.selected_branches = None
        self.branches_skipped = set()
        self.branches_failed = set()

    def add_options(self):
        self.add_opt('-b', '--branch-prefix', help='Branch prefix regex to check')

    def run(self):
        if not self.args:
            self.usage('no Dockerfile / directory args given')
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
            self.check_git_branches_dockerfiles(arg)
        log.info('Total Branches: %s', len(self.branches))
        log.info('Selected Branches: %s', len(self.selected_branches))
        log.info('Branches checked: %s', self.branches_checked)
        log.info('Branches with Dockerfile checked: %s', len(self.branches_dockerfile_checked))
        branches_skipped = len(self.branches_skipped)
        if branches_skipped > 0:
            log.warn('{0} branches skipped for not matching expected naming format'
                     .format(branches_skipped))
        branches_not_checked = [branch for branch in self.selected_branches \
                                    if branch not in self.branches_dockerfile_checked]
        if len(branches_not_checked) > 1:
            log.warn('{0} branches not checked (no matching Dockerfile found?): {1}'\
                     .format(len(branches_not_checked), branches_not_checked))
            if log.isEnabledFor(logging.DEBUG):
                log.debug('Branches with no corresponding Dockerfile found:\n%s',
                          '\n'.join(set(self.selected_branches) - set(self.branches_dockerfile_checked)))
        log.info('{0} Dockerfiles checked'.format(len(self.dockerfiles_checked)))
        branches_failed = len(self.branches_failed)
        _ = '{0} Dockerfiles failed validation across {1} branches'.format(self.dockerfiles_failed, branches_failed)
        if branches_failed > 0:
            log.error(_)
        else:
            log.info(_)
        if self.failed:
            log.error('Dockerfile validation FAILED')
            sys.exit(ERRORS['CRITICAL'])
        log.info('Dockerfile validation SUCCEEDED')

    def check_git_branches_dockerfiles(self, target):
        gitroot = find_git_root(target)
        if gitroot is None:
            die('Failed to find git root for target {0}'.format(target))
        log.debug("finding branches for target '{0}'".format(target))
        repo = git.Repo(gitroot)
        #branches = [str(x) for x in repo.refs if isinstance(x, git.refs.remote.RemoteReference)]
        branches = [str(x) for x in repo.refs if isinstance(x, git.Head)]
        branches = [x.split('/')[-1] for x in branches]
        branches = set(branches)
        branches = [x for x in branches if x not in ('HEAD', 'master')]
        self.branches = branches
        if self.branch_prefix is not None:
            log.debug('restricting to branches matching branch prefix')
            branches = [x for x in branches if self.branch_prefix.match(x)]
        self.selected_branches = branches
        #if log.isEnabledFor(logging.DEBUG):
        log.debug('\n\nbranches for target %s:\n\n%s\n', target, '\n'.join(branches))
        # in Travis CI there is no original branch and master branch does not exist, so falling back to assuming master
        # causes failure, better to not check out original branch if you don't know
        #original_branch = 'master'
        original_branch = None
        try:
            try:
                original_branch = repo.active_branch.name
            except TypeError as _:
                pass
            for branch in branches:
                log.debug("checking branch '%s' Dockerfiles for target '%s'", branch, target)
                self.branches_checked += 1
                try:
                    repo.git.checkout(branch)
                except git.GitError as _:
                    die(_)
                self.check_path(target, branch)
        except Exception as _:  # pylint: disable=broad-except
            traceback.print_exc()
            sys.exit(1)
        finally:
            if original_branch != None:
                log.debug("checking out original branch '%s'", original_branch)
                repo.git.checkout(original_branch)

    def branch_version(self, branch):
        branch_base = None
        branch_versions = []
        # if ...-x.y-x.y
        match = self.branch_regex.match(branch)
        if match:
            groups = match.groups()
            #log.debug('groups = %s', groups)
            branch_base = groups[0]
            for version in groups[1:]:
                if version is None:
                    continue
                branch_versions.append(version)
        else:
            log.warn("Failed to match branch format for branch '{0}'".format(branch) +
                     ", code needs extension for this branch naming format")
            self.branches_skipped.add(branch)
            return ('', [])
        log.debug('branch_base = %s', branch_base)
        log.debug('branch_versions = %s', branch_versions)
        return (branch_base, branch_versions)

    @staticmethod
    def normalize_name(name):
        # allow all -dev dirs to match same branch
        # special case for solr -> solrcloud dirs
        name2 = name
        # cassandra-dev  -> cassandra
        # solrcloud-dev  -> solrcloud
        # presto-cli-dev -> presto-cli
        # presto-cli     -> presto
        # solrcloud      -> solr
        # rabbitmq-cluster -> rabbitmq
        name2 = re.sub(pattern=r'-dev$', repl='', string=name2)
        name2 = re.sub(pattern=r'-cli$', repl='', string=name2)
        name2 = re.sub(pattern=r'cloud$', repl='', string=name2)
        name2 = re.sub(pattern=r'-cluster$', repl='', string=name2)
        # don't need this hack, just check for generic java/jdk/jre to match JAVA_VERSION below
        #name2 = re.sub(pattern=r'(?:alpine|centos|debian|ubuntu)-$', repl='', string=name2)
        # special case for Java versions
        if re.search(r'\b(?:java|jre|jdk)\b', name2):
            name2 = 'java'
        # special case for Scala versions
        if re.search(r'\bscala\b', name2):
            name2 = 'scala'
        name2 = name2.lower()
        #log.debug("normalized name '%s' => '%s'", name, name2)
        return name2

    def check_path(self, path, branch):
        status = True
        (branch_base, _) = self.branch_version(branch)
        branch_normalized_name = self.normalize_name(branch_base)
        log.debug('branch normalized name: %s', branch_normalized_name)
        if os.path.isfile(path):
            return self.check_file(path, branch)
        elif os.path.isdir(path):
            if os.path.basename(path) == '.git':
                return True
            for item in os.listdir(path):
                subpath = os.path.join(path, item)
                if os.path.islink(subpath):
                    subpath = os.path.realpath(subpath)
                if os.path.isdir(subpath):
                    subpath_base = os.path.basename(subpath)
                    #log.debug('subpath_base = %s', subpath_base)
                    if self.normalize_name(subpath_base) == branch_normalized_name:
                        if not self.check_path(subpath, branch):
                            status = False
                elif os.path.isfile(subpath):
                    if not self.check_file(subpath, branch):
                        status = False
                elif not os.path.exists(subpath):
                    log.debug("subpath '%s' does not exist in branch '%s', skipping..." % (subpath, branch))
                else:
                    die("failed to determine if subpath '%s' is file or directory in branch '%s'" % (subpath, branch))
        elif not os.path.exists(path):
            log.debug("path '%s' does not exist in branch '%s', skipping..." % (path, branch))
        else:
            die("failed to determine if path '%s' is file or directory in branch '%s'" % (path, branch))
        return status

    def check_file(self, filename, branch):
        if os.path.basename(filename) != 'Dockerfile':
            return True
        parent = os.path.basename(os.path.dirname(os.path.abspath(filename)))
        (branch_base, _) = self.branch_version(branch)
        if self.normalize_name(branch_base) != self.normalize_name(parent):
            log.debug("skipping '{0}' as it's parent directory '{1}' doesn't match branch base '{2}'".
                      format(filename, parent, branch_base))
            return True
        self.valid_git_branches_msg = '%s => OK: git branch %s' % (filename, branch)
        self.invalid_git_branches_msg = "%s => MISMATCH: in branch '%s'" % (filename, branch)
        try:
            if not self.check_dockerfile_arg(filename, branch):
                self.failed = True
                #print(self.invalid_git_branches_msg)
                return False
            # now switched to per branch scan this returns way too much redundant output
            #print(self.valid_git_branches_msg)
        except IOError as _:
            die("ERROR: %s" % _)
        return True

    def check_dockerfile_arg(self, filename, branch):
        log.debug('check_dockerfile_arg({0}, {1})'.format(filename, branch))
        branch_stripped = str(branch).replace('-dev', '')
        (branch_base, branch_versions) = self.branch_version(branch_stripped)
        with open(filename) as filehandle:
            version_index = 0
            for line in filehandle:
                #log.debug(line.strip())
                # hack for Scala Java version, hacky but can't think of a better more generic way to do this right now
                match = self.arg_regex.match(line.strip())
                if match:
                    arg_var = match.group(1)
                    # this is too restrictive and prevents finding a lot of issues with
                    # more complex naming conventions for kafka, centos-java/scala etc
                    # instead we now expect ARG *_VERSION to be in the same order as the version numbers in branch name
                    #log.debug("checking arg group 1 '%s' == branch_base '%s'", argversion.group(1), branch_base)
                    #if self.normalize_name(arg_var) == self.normalize_name(branch_base).replace('-', '_'):
                    if version_index >= len(branch_versions):
                        return True
                    branch_version = branch_versions[version_index]
                    found_version = match.group(2)
                    if not self.check_version(filename=filename,
                                              branch=branch,
                                              branch_base=branch_base,
                                              arg_var=arg_var,
                                              found_version=found_version,
                                              branch_version=branch_version):
                        return False
                    version_index += 1
                elif branch_base == 'scala' \
                   and len(branch_versions) > 1 \
                   and branch_versions[1] is not None:
                    #log.debug('special scala condition checking for jdk version')
                    match = self.jdk_regex.match(line)
                    if match:
                        found_version = match.group(1)
                        #log.debug('found jdk version \'%s\'', found_version)
                        if not self.check_version(filename=filename,
                                                  branch=branch,
                                                  branch_base=branch_base,
                                                  arg_var=None,
                                                  found_version=found_version,
                                                  branch_version=branch_versions[version_index+1]):
                            return False
        return True

    def check_version(self, filename, branch, branch_base, arg_var, found_version, branch_version):
        self.branches_dockerfile_checked.add(branch)
        self.dockerfiles_checked.add(filename)
        if arg_var:
            log.debug("found arg '%s'", arg_var)
            arg_version = "ARG '{0}={1}'".format(arg_var, found_version)
        else:
            arg_version = "'{0}'".format(found_version)
        #log.debug("arg '%s' matches branch base '%s'", argversion.group(1), branch_base)
        log.debug("comparing '%s' contents to version derived from branch '%s' => '%s'",
                  filename, branch, branch_version)
        if not isVersion(branch_version.lstrip('jdk').lstrip('jre')):
            die("unrecognized branch version '{0}' for branch_base '{1}'"
                .format(branch_version, branch_base))
        #if branch_version == found_version or branch_version == found_version.split('.', 1)[0]:
        if found_version[0:len(branch_version)] == branch_version:
            log.info("{0} version '{1}' matches {2}".
                     format(self.valid_git_branches_msg, branch_version, arg_version))
        else:
            log.error("{0} version '{1}' vs Dockerfile {2}".
                      format(self.invalid_git_branches_msg, branch_version, arg_version))
            self.dockerfiles_failed += 1
            self.branches_failed.add(branch)
            return False
        return True


if __name__ == '__main__':
    DockerfileGitBranchCheckTool().main()

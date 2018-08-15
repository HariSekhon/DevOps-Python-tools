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

Tool to validate Git tags are aligned with any Dockerfiles in that revision which correspond with the tag prefix

Recurses any given directories to find all Dockerfiles and checks their ARG *_VERSION line in each tag
to ensure they're both aligned.

This requires the git tagging and Dockerfile ARG to be aligned in such as way that 'ARG NAME_VERSION=<version>'
corresponds to Git tag 'NAME-<version>' where NAME matches regex '\w+' and <version> is in the form 'x.y[.z]' where if
git tag is at least a prefix of the Dockerfiles ARG version (eg. solr-4 matches ARG SOLR_VERSION=4 and
ARG SOLR_VERSION=4.10).

Additionally, git tags of NAME-dev-<version> are stripped of '-dev' and assumed to still use ARG NAME_VERSION, and the
parent directory name for the Dockerfile must match the tag base without the version (but including the -dev part) in
order to disambiguate between things like SOLRCLOUD_VERSION for either solrcloud/Dockerfile or solrcloud-dev/Docekrfile

Beware this will attempt to do a git checkout of all tags and test containing Dockerfiles under given paths in each tag
revision. If the git checkout is 'dirty' (ie has uncommitted changes) it will prevent checking out the tag, the program
will detect this and exit, leaving you to decide what to do. In normal circumstances it will return to the original
branch/tag checkout when complete.

Prematurely terminating this program can leave the git checkout in an inconsistent state, although all catchable
exceptions are caught to return to original state. If you end up in an inconsistent state just git reset and do a
manual checkout back to master.

Recommended to run this on a non-working git checkout to make it easy to reset state and avoid dirty git checkout
issues eg. run inside your CI system or a secondary git clone location.

Originally this worked on a file-by-file basis which is better when recursing directories across git submodules, but
was the least efficient way of doing it so I've rewritten it to do a single pass of all tags and check all Dockerfiles
in given directories, hence it's more efficient to give this program the directory containing the Dockerfiles than each
individual Dockerfile which would result in a similar behaviour to the original, multiplying each Dockerfile by the
number of tags and doing that many checkouts.

It is more efficient to give a directory tree of Dockerfiles than individual Dockerfiles... but the caveat is that they
must all be contained in the same Git repo (not crossing git submodule boundaries etc, otherwise you must do a
'find -exec' using this program instead).

This is one of the my less generic tools in the public domain. It requires your use of git tags matches your use of
Dockerfile ARG. You're welcome to modify it to suit your needs or make it more generic (in which case please
re-submit improvements in the form for GitHub pull requests).

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import re
import sys
import git
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, find_git_root, log, log_option
    from harisekhon.utils import uniq_list_ordered, isVersion, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.2'

class DockerfileGitTagCheckTool(CLI):

    def __init__(self):
        # Python 2.x
        super(DockerfileGitTagCheckTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.failed = False
                                       # ARG ZOOKEEPER_VERSION=3.4.8
        self.arg_regex = re.compile(r'^\s*ARG\s+([\w_]+)_VERSION=([\w\.]+)\s*')
        self.tag_prefix = None
        self.timeout_default = 86400
        self.valid_git_tags_msg = None
        self.invalid_git_tags_msg = None
        self.verbose_default = 2

    def add_options(self):
        self.add_opt('-T', '--tag-prefix', help='Tag prefix regex to check')

    def run(self):
        if not self.args:
            self.usage('no Dockerfile / directory args given')
        args = uniq_list_ordered(self.args)
        self.tag_prefix = self.get_opt('tag_prefix')
        if self.tag_prefix is not None:
            validate_regex(self.tag_prefix, 'tag prefix')
            self.tag_prefix = re.compile(self.tag_prefix)
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
            self.check_git_tags_dockerfiles(arg)
        if self.failed:
            log.error('Dockerfile validation FAILED')
            sys.exit(ERRORS['CRITICAL'])
        log.info('Dockerfile validation SUCCEEDED')

    def check_git_tags_dockerfiles(self, target):
        target = os.path.abspath(target)
        gitroot = find_git_root(target)
        log.debug("finding tags for target '{0}'".format(target))
        repo = git.Repo(gitroot)
        tags = [str(x).split('/')[-1] for x in repo.tags]
        if self.tag_prefix is not None:
            log.debug('restricting to tags matching tag prefix')
            tags = [x for x in tags if self.tag_prefix.match(x)]
        #if log.isEnabledFor(logging.DEBUG):
        log.debug('\n\ntags for target %s:\n\n%s\n', target, '\n'.join(tags))
        original_checkout = 'master'
        try:
            try:
                original_checkout = repo.active_branch.name
            except TypeError as _:
                pass
            for tag in tags:
                log.debug("checking tag '%s' Dockerfiles for target '%s'", tag, target)
                try:
                    repo.git.checkout(tag)
                except git.GitError as _:
                    die(_)
                self.check_path(target, tag)
        except Exception as _:  # pylint: disable=broad-except
            die(_)
        finally:
            log.debug("returning to original checkout '%s'", original_checkout)
            repo.git.checkout(original_checkout)

    def check_path(self, path, tag):
        status = True
        if os.path.isfile(path):
            return self.check_file(path, tag)
        elif os.path.isdir(path):
            if os.path.basename(path) == '.git':
                return True
            for item in os.listdir(path):
                subpath = os.path.join(path, item)
                if os.path.islink(subpath):
                    subpath = os.path.realpath(subpath)
                if os.path.isdir(subpath):
                    tag_base = tag.rsplit('-', 1)[0]
                    subpath_base = os.path.basename(subpath)
                    #log.debug('tag_base = %s', tag_base)
                    #log.debug('subpath_base = %s', subpath_base)
                    if subpath_base == tag_base:
                        if not self.check_path(subpath, tag):
                            status = False
                elif os.path.isfile(subpath):
                    if not self.check_file(subpath, tag):
                        status = False
                elif not os.path.exists(subpath):
                    log.debug("subpath '%s' does not exist in tag '%s', skipping..." % (subpath, tag))
                else:
                    die("failed to determine if subpath '%s' is file or directory in tag '%s'" % (subpath, tag))
        elif not os.path.exists(path):
            log.debug("path '%s' does not exist in tag '%s', skipping..." % (path, tag))
        else:
            die("failed to determine if path '%s' is file or directory in tag '%s'" % (path, tag))
        return status

    def check_file(self, filename, tag):
        filename = os.path.abspath(filename)
        if os.path.basename(filename) != 'Dockerfile':
            return True
        parent = os.path.basename(os.path.dirname(filename))
        tag_base = tag.rsplit('-', 1)[0]
        if parent.lower() != tag_base.lower():
            log.debug("skipping '{0}' as it's parent directory '{1}' doesn't match tag base '{2}'".
                      format(filename, parent, tag_base))
            return True
        self.valid_git_tags_msg = '%s => Dockerfile Git Tags OK' % filename
        self.invalid_git_tags_msg = "%s => Dockerfile Git Tags MISMATCH in tag '%s'" % (filename, tag)
        try:
            if not self.check_dockerfile_arg(filename, tag):
                self.failed = True
                #print(self.invalid_git_tags_msg)
                return False
            # now switched to per tag scan this returns way too much redundant output
            #print(self.valid_git_tags_msg)
        except IOError as _:
            die("ERROR: %s" % _)
        return True

    def check_dockerfile_arg(self, filename, tag):
        log.debug('check_dockerfile_arg({0}, {1})'.format(filename, tag))
        tag_base = str(tag).replace('-dev', '')
        (tag_base, tag_version) = tag_base.rsplit('-', 1)
        log.debug('tag_base = {0}'.format(tag_base))
        log.debug('tag_version = {0}'.format(tag_version))
        with open(filename) as filehandle:
            for line in filehandle:
                #log.debug(line.strip())
                argversion = self.arg_regex.match(line.strip())
                if argversion:
                    log.debug("found arg '%s'", argversion.group(0))
                    log.debug("checking arg group 1 '%s' == tag_base '%s'", argversion.group(1), tag_base)
                    if argversion.group(1).lower() == tag_base.lower().replace('-', '_'):
                        log.debug("arg '%s'  matches tag base '%s'", argversion.group(1), tag_base)
                        log.debug("comparing '%s' contents to version derived from tag '%s' => '%s'",
                                  filename, tag, tag_version)
                        if not isVersion(tag_version):
                            die("unrecognized tag version '{0}' for tag_base '{1}'".format(tag_version, tag_base))
                        found_version = argversion.group(2)
                        #if tag_version == found_version or tag_version == found_version.split('.', 1)[0]:
                        if found_version[0:len(tag_version)] == tag_version:
                            log.info("{0} (tag version '{1}' matches arg version '{2}')".
                                     format(self.valid_git_tags_msg, tag_version, found_version))
                            return True
                        log.error('{0} ({1} tag vs {2} Dockerfile ARG)'.
                                  format(self.invalid_git_tags_msg, tag_version, found_version))
                        return False
        return True

# a per file method, better for recursing across git submodules but much more brute force as a cartesian product of
# tags vs Dockerfiles rather than a single pass of tags within one repo
#
#    def check_dockerfile_git_tags(self, filename):
#        filename = os.path.abspath(filename)
#        gitroot = self.find_git_root(filename)
#        log.debug("finding tags for file '{0}' from git root '{1}'".format(filename, gitroot))
#        repo = git.Repo(gitroot)
#        tags = [str(_).split('/')[-1] for _ in repo.tags]
#        #if log.isEnabledFor(logging.DEBUG):
#        log.debug('\n\ntags for Dockerfile %s:\n\n%s\n', filename, '\n'.join(tags))
#        dirname = os.path.dirname(filename)
#        original_dir = os.getcwd()
#        log.debug('cd %s', dirname)
#        os.chdir(dirname)
#        original_checkout = 'master'
#        try:
#            try:
#                original_checkout = repo.active_branch.name
#            except TypeError as _:
#                pass
#            for tag in repo.tags:
#                log.debug("checking file '%s' checking out tag '%s'", filename, tag)
#                try:
#                    repo.git.checkout(tag)
#                except git.exc.GitCommandError as _:
#                    die(_)
#                try:
#                    if not self.check_dockerfile_arg(filename, tag):
#                        self.failed = True
#                        print(self.invalid_git_tags_msg)
#                        return False
#                except IOError as _:
#                    log.warn(str(_) + " ('{0}' probably doesn't exist in tag revision '{1}')".format(filename, tag))
#            print(self.valid_git_tags_msg)
#            return True
#        except Exception as _:
#            die(_)
#        finally:
#            log.debug("returning to original checkout '%s'", original_checkout)
#            repo.git.checkout(original_checkout)
#            log.debug("cd %s", original_dir)
#            os.chdir(original_dir)


if __name__ == '__main__':
    DockerfileGitTagCheckTool().main()

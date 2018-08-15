#!/usr/bin/env python
#
#  Author: Hari Sekhon
#  Date: 6/8/2014
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying LICENSE file
#

"""
Starts a unique password protected instance of IPython Notebook integrated with PySpark
for the user running this program.

This is a workaround to IPython Notebook not have multi-user support as of 2014.

Supports shell environment variables:

Required:

    - ipython must be in $PATH
    - $SPARK_HOME (this is how IPython finds pyspark)

Optional:

    - $HADOOP_CONF_DIR / $YARN_CONF_DIR (defaults to /etc/hadoop/conf)
    - $SPARK_YARN_USR_ENV
    - $PYSPARK_SUBMIT_ARGS (defaults to 5 executors, 5 cores, 10GB)

Prompts for a password if none has been set before.

Then creates a new IPython Notebook configuration for PySpark and boots.

Uses Jinja2 template files co-located in the same directory as this program:

.ipython-notebook-pyspark.00-pyspark-setup.py
.ipython-notebook-pyspark.ipython_notebook_config.py.j2

Tested on Spark 1.0.x on Hortonworks 2.1 (Yarn + Standalone) and IBM BigInsights 2.1.2 (Standalone)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import getpass
import glob
import os
import shutil
import sys
import time
from jinja2 import Template
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import isLinux, isMac, isIP, isPythonMinVersion, ERRORS, printerr, warn, pyspark_path
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)
pyspark_path()

__author__ = 'Hari Sekhon'
__version__ = '0.3.2'

if not isPythonMinVersion(2.7):
    warn('Python < 2.7 - IPython may not be available on this version of Python ' +
         '(supplied auto-build will likely have failed for this module)\n')
try:
    # pylint: disable=wrong-import-position
    from IPython.lib import passwd
except ImportError as _:
    printerr("""failed to import from IPython.lib

Perhaps you need to 'pip install \"ipython[notebook]\"'

Exception message: %s""" % _)
    if not isPythonMinVersion(2.7):
        printerr('Python < 2.7 - the supplied make auto build with this tool probably failed ' +
                 'to install IPython because IPython requires Python >= 2.7')
        sys.exit(ERRORS['UNKNOWN'])
    sys.exit(ERRORS['CRITICAL'])

# Mac now supported
#try:
#    linux_only()
#except LinuxOnlyException, e:
#    die(e)

# TODO: rewrite from here as a CLI class, not using globals

if len(sys.argv) > 1:
    printerr("""Hari Sekhon - https://github.com/harisekhon/devops-python-tools

usage: %s

version %s
%s""" % (os.path.basename(sys.argv[0]), __version__, __doc__))
    sys.exit(3)

srcdir = os.path.abspath(os.path.dirname(sys.argv[0]))

###########################
# PySpark Settings
#

## local mode - default anyway just give it 2 cores
#default_master = "local[2]"

## standalone master mode
#default_master = "spark://master:7077"

## Yarn mode - this is what I use now on Hortonworks
default_master = "yarn_client"

master = os.getenv('MASTER', default_master)

# defaults resources to use if not setting PYSPARK_SUBMIT_ARGS
num_executors = 5
executor_cores = 5
executor_memory = "10g"

SPARK_HOME = os.getenv('SPARK_HOME', None)
if SPARK_HOME:
    os.environ['PATH'] = "%s:%s/bin" % (os.getenv("PATH", ""), SPARK_HOME)
else:
    print("SPARK_HOME needs to be set (eg. export SPARK_HOME=/opt/spark)")
    sys.exit(4)

# Workaround to assembly jar not providing pyspark on Yarn and PythonPath not being passed through normally
#
# Error from python worker:
#  /usr/bin/python: No module named pyspark
# PYTHONPATH was:
#  /data1/hadoop/yarn/local/usercache/hari/filecache/14/spark-assembly-1.0.2-hadoop2.4.0.jar
#
# this isn't enough because the PYTHONPATH isn't passed through to Yarn - also it's set my pyspark wrapper anyway
# so this is actually to generate SPARK_YARN_USER_ENV which allows the pyspark to execute across the cluster
# this will probably get fixed up and be unneccessary in future
#os.environ['PYTHONPATH'] = os.getenv('PYTHONPATH', '') + ":%s/python" % SPARK_HOME
sys.path.insert(0, os.path.join(SPARK_HOME, 'python'))
for lib in glob.glob(os.path.join(SPARK_HOME, 'python/lib/py4j-*-src.zip')):
    sys.path.insert(0, lib)
#
# simply appending causes an Array error in Java due to the first element
# being empty if SPARK_YARN_USER_ENV isn't already set
if os.getenv('SPARK_YARN_USER_ENV', None):
    os.environ['SPARK_YARN_USER_ENV'] = os.environ['SPARK_YARN_USER_ENV'] + ",PYTHONPATH=" + ":".join(sys.path)
else:
    os.environ['SPARK_YARN_USER_ENV'] = "PYTHONPATH=" + ":".join(sys.path)

# Set some sane likely defaults
if not (os.getenv('HADOOP_CONF_DIR', None) or os.getenv('YARN_CONF_DIR', None)):
    print("warning: YARN_CONF_DIR not set, temporarily setting /etc/hadoop/conf")
    os.environ['YARN_CONF_DIR'] = '/etc/hadoop/conf'

if not os.getenv('PYSPARK_SUBMIT_ARGS', None):
    # don't hog the whole cluster - limit executor / RAM / CPU usage
    os.environ['PYSPARK_SUBMIT_ARGS'] = "--num-executors %d --total-executor-cores %d --executor-memory %s" \
                                        % (num_executors, executor_cores, executor_memory)
os.environ['PYSPARK_SUBMIT_ARGS'] = "--master %s %s" % (master, os.environ['PYSPARK_SUBMIT_ARGS'])

###########################
# IPython Notebook Settings
template_file = srcdir + "/.ipython-notebook-pyspark.ipython_notebook_config.py.j2"
pyspark_startup_src = srcdir + "/.ipython-notebook-pyspark.00-pyspark-setup.py"

# Set default to 0.0.0.0 for portability but better set to your IP
# for IPython output to give the correct URL to users
default_ip = "0.0.0.0"

# try setting to the main IP with default gw to give better feedback to user where to connect
if isLinux():
    ip = os.popen("ifconfig $(netstat -rn | awk '/^0.0.0.0[[:space:]]/ {print $8}') | sed -n '2 s/.*inet addr://; 2 s/ .*// p'").read().rstrip('\n') # pylint: disable=line-too-long
elif isMac():
    ip = os.popen("ifconfig $(netstat -rn | awk '/^default[[:space:]]/ {print $6}') | sed -n '4 s/.*inet //; 4 s/ .*// p'").read().rstrip('\n') # pylint: disable=line-too-long
else:
    warn('OS is not Linux or Mac, IP detection will not work')
if not isIP(ip):
    warn('defaulting IP to %s' % default_ip)
    ip = default_ip

ipython_profile_name = "pyspark"
###########################


template = Template(open(template_file).read())

password = "1"
password2 = "2"

if getpass.getuser() == 'root':
    print("please run this as your regular user account and not root!")
    sys.exit(1)

def get_password():
    global password
    global password2
    #password  = raw_input("Enter password to protect your personal IPython NoteBook\n\npassword: ")
    #password2 = raw_input("confirm password: ")
    print("\nEnter a password to protect your personal IPython NoteBook (sha1 hashed and written to a config file)\n")
    password = getpass.getpass()
    password2 = getpass.getpass("Confirm Password: ")

try:
    ipython_profile = os.popen("ipython locate").read().rstrip("\n") + "/profile_%s" % ipython_profile_name
    ipython_notebook_config = ipython_profile + "/ipython_notebook_config.py"
    passwd_txt = ipython_profile + "/passwd.txt"
    setup_py = ipython_profile + "/startup/00-pyspark-setup.py"

    if not os.path.exists(ipython_profile):
        print("creating new ipython notebook profile")
        cmd = "ipython profile create %s" % ipython_profile_name
        #print(cmd)
        os.system(cmd)

    if not os.path.exists(passwd_txt):
        get_password()
        while password != password2:
            print("passwords do not match!\n")
            get_password()
        print("writing new encrypted password")
        passwd_fh = open(passwd_txt, "w")
        passwd_fh.write(passwd(password))
        passwd_fh.close()
        os.chmod(passwd_txt, 0o600)

    #if not os.path.exists(setup_py):
    shutil.copy(pyspark_startup_src, setup_py)
    os.chmod(setup_py, 0o600)

    try:
        ipython_notebook_config_contents = open(ipython_notebook_config).read()
    except IOError:
        ipython_notebook_config_contents = ""
    if not os.path.exists(ipython_notebook_config) or passwd_txt not in ipython_notebook_config_contents \
        or "c.NotebookApp.ip = '%s'" % ip not in ipython_notebook_config_contents:
        print("writing new ipython notebook config")
        config = open(ipython_notebook_config, "w")
        config.write(template.render(passwd_txt=passwd_txt,
                                     ip=ip,
                                     name=os.path.basename(sys.argv[0]),
                                     date=time.ctime(),
                                     template_path=template_file))
        config.close()
        os.chmod(ipython_notebook_config, 0o600)
    # PYSPARK_SUBMIT_ARGS is reset to "" by pyspark wrapper script, call IPython Notebook drectly to avoid this :-/
    #cmd = "IPYTHON_OPTS='notebook --profile=%s' pyspark" % ipython_profile_name
    cmd = "ipython notebook --profile=%s" % ipython_profile_name
    #print("PYSPARK_SUBMIT_ARGS=%s" % os.environ['PYSPARK_SUBMIT_ARGS'])
    #print(cmd)
    os.system(cmd)
except KeyboardInterrupt:
    pass

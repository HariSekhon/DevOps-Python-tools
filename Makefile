#
#  Author: Hari Sekhon
#  Date: 2013-02-03 10:25:36 +0000 (Sun, 03 Feb 2013)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying LICENSE file
#
#  https://www.linkedin.com/in/harisekhon
#

# Travis has custom python install earlier in $PATH even in Perl builds so need to install PyPI modules to non-system python otherwise they're not found by programs.
# Better than modifying $PATH to put /usr/bin first which is likely to affect many other things including potentially not finding the perlbrew installation first

# ===================
# bootstrap commands:

# setup/bootstrap.sh
#
# OR
#
# Alpine:
#
#   apk add --no-cache git make && git clone https://github.com/harisekhon/devops-python-tools pytools && cd pytools && make
#
# Debian / Ubuntu:
#
#   apt-get update && apt-get install -y make git && git clone https://github.com/harisekhon/devops-python-tools pytools && cd pytools && make
#
# RHEL / CentOS:
#
#   yum install -y make git && git clone https://github.com/harisekhon/devops-python-tools pytools && cd pytools && make

# ===================

# would fail bootstrapping on Alpine
#SHELL := /usr/bin/env bash

ifneq ("$(wildcard bash-tools/Makefile.in)", "")
	include bash-tools/Makefile.in
endif

REPO := HariSekhon/DevOps-Python-tools

CODE_FILES := $(shell find . -type f -name '*.py' -o -type f -name '*.sh' | grep -v -e bash-tools -e /pylib/)

# placeholders to silence check_makefile.sh warnings - should be set in client Makefiles after sourcing
ifndef PARQUET_VERSION
	PARQUET_VERSION :=
endif
ifndef SKIP_PARQUET
	SKIP_PARQUET :=
endif

.PHONY: build
build: init
	@echo =========================
	@echo DevOps Python Tools Build
	@echo =========================
	@$(MAKE) git-summary
	@echo
	# defer via external sub-call, otherwise will result in error like
	# make: *** No rule to make target 'python-version', needed by 'build'.  Stop.
	@$(MAKE) python-version

	if [ -z "$(CPANM)" ]; then make; exit $$?; fi
	$(MAKE) system-packages-python
	if type apk 2>/dev/null; then $(MAKE) apk-packages-extra; fi
	if type apt-get 2>/dev/null; then $(MAKE) apt-packages-extra; fi

	$(MAKE) python

.PHONY: init
init:
	git submodule update --init --recursive

.PHONY: python
python:
	# defer via external sub-call, otherwise will result in error like
	# make: *** No rule to make target 'python-version', needed by 'build'.  Stop.
	@$(MAKE) python-version
	cd pylib && $(MAKE)
	@# don't pull parquet tools in to docker image by default, will bloat it
	@# can fetch separately by running 'make parquet-tools' if you really want to
	@if [ -f /.dockerenv -o -n "$(SKIP_PARQUET)" ]; then \
		echo; echo; \
		echo "Skipping Parquet install..."; \
		echo; echo; \
	else \
		$(MAKE) parquet-tools; \
	fi

	@# only install pip packages not installed via system packages
	@#$(SUDO_PIP) pip install --upgrade -r requirements.txt
	@#$(SUDO_PIP) pip install -r requirements.txt
	@PIP_OPTS="--ignore-installed" bash-tools/python_pip_install_if_absent.sh requirements.txt

	@# python-krbV dependency doesn't build on Mac any more and is unmaintained and not ported to Python 3
	@# python_pip_install_if_absent.sh would import snakebite module and not trigger to build the enhanced snakebite with [kerberos] bit
	bash-tools/setup/python_install_snakebite.sh

	# Python >= 3.4 - try but accept failure in case we're not on the right version of Python
	@#if [ "$$(echo "$$(python -V 2>&1 | grep -Eo '[[:digit:]]+\.[[:digit:]]+') >= 3.4" | bc -l)" = 1 ]; then bash-tools/python_pip_install.sh "avro-python3"; fi
	bash-tools/python_pip_install.sh "avro-python3" || :

	@# for impyla
	@#$(SUDO_PIP) pip install --upgrade setuptools || :
	@#
	@# snappy may fail to install on Mac not finding snappy-c.h - workaround:
	@#
	@# brew install snappy
	@#
	@# find /usr/local -name snappy-c.h
	@#
	@# /usr/local/include/snappy-c.h
	@#
	@# sudo su
	@# LD_RUN_PATH=/usr/local/include pip install snappy
	@#
	@#$(SUDO_PIP) pip install --upgrade -r requirements.txt

	@# for ipython-notebook-pyspark.py
	@#$(SUDO_PIP) pip install jinja2
	@# HiveServer2
	@#$(SUDO_PIP) pip install pyhs2
	@# Impala
	@#$(SUDO_PIP) pip install impyla
	@# must downgrade happybase library to work on Python 2.6
	@#if [ "$$(python -c 'import sys; sys.path.append("pylib"); import harisekhon; print(harisekhon.utils.getPythonVersion())')" = "2.6" ]; then $(SUDO_PIP) pip install --upgrade "happybase==0.9"; fi

	@# Python >= 2.7 - won't build on 2.6, handle separately and accept failure
	@bash-tools/python_pip_install.sh "ipython[notebook]" || :
	@echo
	$(MAKE) pycompile
	@echo
	@echo
	$(MAKE) spark-deps
	@echo
	@echo 'BUILD SUCCESSFUL (pytools)'

.PHONY: parquet-tools
parquet-tools:
	@BIN='.' bash-tools/setup/install_parquet-tools.sh

.PHONY: apk-packages-extra
apk-packages-extra:
	if [ -z "$(NOJAVA)" ]; then which java || $(SUDO) apk add openjdk8-jre-base; fi
	# Spark Java Py4J gets java linking error without this
	if [ -f /lib/libc.musl-x86_64.so.1 ]; then [ -e /lib/ld-linux-x86-64.so.2 ] || ln -sv /lib/libc.musl-x86_64.so.1 /lib/ld-linux-x86-64.so.2; fi

.PHONY: apt-packages-extra
apt-packages-extra:
	if [ -z "$(NOJAVA)" ]; then which java || $(SUDO) apt-get install -y default-jdk; fi

# for validate_multimedia.py
# available in Alpine 2.6, 2.7 and 3.x
.PHONY: apk-packages-multimedia
apk-packages-multimedia:
	$(SUDO) apk update
	$(SUDO) apk add ffmpeg

# for validate_multimedia.py
# Ubuntu 16.04 Xenial onwards, not available in Ubuntu 14.04 Trusty
# Debian 9 Stretch onwards, not available in Debian 8 Jessie
.PHONY: apt-packages-multimedia
apt-packages-multimedia:
	$(SUDO) apt-get update
	$(SUDO) apt-get install -y --no-install-recommends ffmpeg

# for validate_multimedia.py
.PHONY: yum-packages-multimedia
yum-packages-multimedia:
	@echo "This requires 3rd party rpm repos which could result in rpm hell, please handle this manually yourself so you understand what you're doing"
	exit 1

.PHONY: jython
jython:
	if [ -x /sbin/apk ];        then apk add --no-cache wget expect; fi
	if [ -x /usr/bin/apt-get ]; then apt-get install -y wget expect; fi
	if [ -x /usr/bin/yum ];     then yum install -y wget expect; fi
	sh jython_install.sh

.PHONY: test-lib
test-lib:
	cd pylib && $(MAKE) test

.PHONY: test
test: test-lib
	tests/all.sh

.PHONY: basic-test
basic-test: test-lib
	bash-tools/check_all.sh

.PHONY: install
install: build
	@echo "No installation needed, just add '$(PWD)' to your \$$PATH"

.PHONY: clean
clean:
	cd pylib && $(MAKE) clean
	@# the xargs option to ignore blank input doesn't work on Mac
	@find . -iname '*.py[co]' -o -iname '*.jy[co]' | xargs rm -f
	@find . -iname '*.spec' | xargs rm -f
	@find . -type d -ipath '*/tests/*' -iname 'test-*spark*.avro' | xargs rm -rf
	@find . -type d -ipath '*/tests/*' -iname 'test-*spark*.parquet' | xargs rm -rf
	@rm -f parquet-tools-$(PARQUET_VERSION)-bin.zip
	@if test -f /.dockerenv; then echo "detected running in Docker, removing Spark tarballs for space efficiency" && rm -fr tests/spark-*-bin-hadoop*; fi

.PHONY: deep-clean
deep-clean: clean
	cd pylib && $(MAKE) deep-clean

.PHONY: spark-deps
spark-deps:
	rm -vf spark-deps.zip
	zip spark-deps.zip pylib

.PHONY: dockerhub-trigger
dockerhub-trigger:
	# PyTools
	curl --header "Content:Type:application/json" --data '{"build":true}' -X POST https://cloud.docker.com/api/build/v1/source/d470810b-9a44-4abc-92cc-c903a6afd962/trigger/0e69c39f-ea1b-43c7-a97d-cef1252f1400/call/
	# Alpine Github
	curl --header "Content:Type:application/json" --data '{"build":true}' -X POST https://cloud.docker.com/api/build/v1/source/df816f2a-9407-4f1b-8b51-39615d784e65/trigger/8d9cb826-48df-439c-8c20-1975713064fc/call/
	# Debian Github
	curl --header "Content:Type:application/json" --data '{"build":true}' -X POST https://cloud.docker.com/api/build/v1/source/439eff84-50c7-464a-a49e-0ac0bf1a9a43/trigger/0cfb3fe7-2028-494b-a43b-068435e6a2b3/call/
	# CentOS Github
	curl --header "Content:Type:application/json" --data '{"build":true}' -X POST https://cloud.docker.com/api/build/v1/source/efba1846-5a9e-470a-92f8-69edc1232ba0/trigger/316d1158-7ffb-49a4-a7bd-8e5456ba2d15/call/
	# Ubuntu Github
	curl --header "Content:Type:application/json" --data '{"build":true}' -X POST https://cloud.docker.com/api/build/v1/source/8b3dc094-d4ca-4c92-861e-1e842b5fac42/trigger/abd4dbf0-14bc-454f-9cde-081ec014bc48/call/

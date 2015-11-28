#
#  Author: Hari Sekhon
#  Date: 2013-02-03 10:25:36 +0000 (Sun, 03 Feb 2013)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying LICENSE file
#

ifdef TRAVIS
	SUDO2 =
else
	SUDO2 = sudo
endif

# EUID /  UID not exported in Make
# USER not populated in Docker
ifeq '$(shell id -u)' '0'
	SUDO =
	SUDO2 =
else
	SUDO = sudo
endif

.PHONY: make
make:
	[ -x /usr/bin/apt-get ] && make apt-packages || :
	[ -x /usr/bin/yum ]     && make yum-packages || :

	git submodule init
	git submodule update

	cd pylib && make

	# json module built-in to Python >= 2.6, backport not available via pypi
	#$(SUDO2) pip install json

	# for ipython-notebook-pyspark.py
	$(SUDO2) pip install jinja2

	# Python >= 2.7 - won't build on 2.6
	$(SUDO2) pip install "ipython[notebook]"

	# HiveServer2
	$(SUDO2) pip install pyhs2

	# Impala
	$(SUDO2) pip install impyla

	@echo
	@echo BUILD SUCCESSFUL

.PHONY: apt-packages
apt-packages:
	$(SUDO) apt-get install -y gcc
	# needed to fetch the library submodule at end of build
	$(SUDO) apt-get install -y git
	$(SUDO) apt-get install -y ipython-notebook
	dpkg -l python-setuptools python-dev &>/dev/null || $(SUDO) apt-get install -y python-setuptools python-dev

.PHONY: yum-packages
yum-packages:
	rpm -q gcc || $(SUDO) yum install -y gcc
	# needed to fetch the library submodule and CPAN modules
	# python-pip requires EPEL, so try to get the correct EPEL rpm - for Make must escape the $3
	rpm -ivh "https://dl.fedoraproject.org/pub/epel/epel-release-latest-`awk '{print substr($$3, 0, 1); exit}' /etc/*release`.noarch.rpm"
	rpm -q python-setuptools python-pip python-devel || $(SUDO) yum install -y python-setuptools python-pip python-devel
	rpm -q ipython-notebook || $(SUDO) yum install -y ipython-notebook
	# needed to build pyhs2
	# libgsasl-devel saslwrapper-devel
	rpm -q cyrus-sasl-devel || $(SUDO) yum install -y cyrus-sasl-devel

.PHONY: test
test:
	cd pylib && make test
	tests/all.sh

.PHONY: install
install:
	@echo "No installation needed, just add '$(PWD)' to your \$$PATH"

.PHONY: update
update:
	make update2
	make
	make test

.PHONY: update2
update2:
	git pull
	git submodule update --init

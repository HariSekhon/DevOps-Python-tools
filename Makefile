#
#  Author: Hari Sekhon
#  Date: 2013-02-03 10:25:36 +0000 (Sun, 03 Feb 2013)
#
#  http://github.com/harisekhon/pytools
#
#  License: see accompanying LICENSE file
#

ifdef TRAVIS
    SUDO2 =
else
    SUDO2 = sudo
endif

# EUID /  UID not exported in Make
ifeq '$(USER)' 'root'
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

	cd lib && make

	# for ipython-notebook-pyspark.py
	pip install jinja2
	# Python >= 2.7 - won't build on 2.6
	pip install "ipython[notebook]" || :
	# HiveServer2
	pip install pyhs2 || :

.PHONY: apt-packages
apt-packages:
	$(SUDO) apt-get install -y gcc || :
	# needed to fetch the library submodule at end of build
	$(SUDO) apt-get install -y git || :
	$(SUDO) apt-get install -y ipython-notebook || :
	dpkg -l python-setuptools python-dev &>/dev/null || $(SUDO) apt-get install -y python-setuptools python-dev || :

.PHONY: yum-packages
yum-packages:
	rpm -q gcc || $(SUDO) yum install -y gcc || :
	# needed to fetch the library submodule and CPAN modules
	# python-pip requires EPEL, so try to get the correct EPEL rpm - for Make must escape the $3
	rpm -ivh "https://dl.fedoraproject.org/pub/epel/epel-release-latest-`awk '{print substr($$3, 0, 1); exit}' /etc/*release`.noarch.rpm" || :
	rpm -q python-setuptools python-pip python-devel || $(SUDO) yum install -y python-setuptools python-pip python-devel || :
	rpm -q ipython-notebook || $(SUDO) yum install -y ipython-notebook || :
	# needed to build pyhs2
	# libgsasl-devel saslwrapper-devel
	rpm -q cyrus-sasl-devel || $(SUDO) yum install -y cyrus-sasl-devel || :

.PHONY: test
test:
	cd lib && make test
	tests/help.sh
	for x in tests/*.sh; do [ "$$x" = "tests/help.sh" ] && continue; ./$$x || exit $$?; done

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

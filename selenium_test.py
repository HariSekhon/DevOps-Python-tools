#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2021-05-12 09:55:01 +0100 (Wed, 12 May 2021)
#
#  https://github.com/HariSekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/HariSekhon
#

"""

Tests a Selenium Hub / Selenoid using the given capability eg. FIREFOX, CHROME
against a given URL and content (defaults to google.com)

Example:

    ./selenium_test.py --host <selenium_hub_host> [options] <capabilities>

    ./selenium_test.py --host selenium-hub FIREFOX CHROME

    ./selenium_test.py --host selenium-hub FIREFOX CHROME --url google.com --content google
    ./selenium_test.py --host selenium-hub FIREFOX CHROME --url google.com --regex 'goog.*'

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import sys
import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log
    from harisekhon.utils import validate_host, validate_port, validate_url, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


class SeleniumTest(CLI):

    def __init__(self):
        # Python 2.x
        super(SeleniumTest, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host = None
        self.port = None
        self.protocol = 'http'
        self.name = 'Selenium Hub'
        self.default_port = 80
        self.path = 'wd/hub'
        self.url_default = 'http://google.com'
        self.url = self.url_default
        self.expected_content = None
        self.expected_regex = None
        self.timeout_default = 600
        self.verbose_default = 2

    def add_options(self):
        super(SeleniumTest, self).add_options()
        self.add_hostoption(name='Selenium Hub', default_port=4444)
        self.add_opt('-u', '--url', default=self.url_default,
                     help='URL to use for the test (default: {})'.format(self.url_default))
        self.add_opt('-c', '--content', help='URL content to expect')
        self.add_opt('-r', '--regex', help='URL content to expect')
        self.add_opt('-S', '--ssl', action='store_true', help='Use SSL to connect to Selenium Hub')

    def process_options(self):
        super(SeleniumTest, self).process_options()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        self.url = self.get_opt('url')
        if ':' not in self.url:
            self.url = 'http://' + self.url
        self.expected_content = self.get_opt('content')
        self.expected_regex = self.get_opt('regex')
        if self.expected_regex:
            validate_regex(self.expected_regex)
            self.expected_regex = re.compile(self.expected_regex)
        validate_host(self.host)
        validate_port(self.port)
        validate_url(self.url)
        if self.get_opt('ssl'):
            self.protocol = 'https'
        if not self.args:
            self.usage()

    def check_selenium(self, capability, url):
        selenium_url = '{protocol}://{host}:{port}/{path}'\
                    .format(protocol=self.protocol, \
                            host=self.host, \
                            port=self.port, \
                            path=self.path)
        log.info("Connecting to '%s' with capability '%s'", selenium_url, capability)
        driver = webdriver.Remote(
            command_executor=selenium_url,
            desired_capabilities=getattr(DesiredCapabilities, capability)
        )
        log.info("Checking url '%s'", url)
        driver.get(self.url)
        content = driver.page_source
        if self.expected_content:
            log.info("Checking url content matches '%s'", self.expected_content)
            if self.expected_content not in content:
                raise AssertionError('Page source content failed content match')
        if self.expected_regex:
            log.info("Checking url content matches regex")
            if not self.expected_regex.search(content):
                raise AssertionError('Page source content failed regex search')
        driver.quit()
        log.info("Succeeded with capability '%s' against url '%s'", capability, url)

    def run(self):
        start_time = time.time()
        for capability in self.args:
            self.check_selenium(capability, self.url)
        query_time = time.time() - start_time
        log.info('Finished checks in {:.2f} secs'.format(query_time))


if __name__ == '__main__':
    SeleniumTest().main()

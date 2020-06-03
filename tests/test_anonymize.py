#!/usr/bin/env python

from __future__ import print_function

import os
import re
#import StringIO
import subprocess
from subprocess import PIPE
import sys

srcdir = os.path.abspath(os.path.dirname(__file__))

anonymize_test_sh = os.path.join(srcdir, 'test_anonymize.sh')

anonymize = '{}/../anonymize.py'.format(srcdir)

src = {}
dest = {}

src_regex = re.compile(r'^\s*src\[(\d+)\]=["\'](.+)["\']\s*$')
dest_regex = re.compile(r'^\s*dest\[(\d+)\]=["\'](.+)["\']\s*$')
args_regex = re.compile(r'^\s*args=["\'](.+)["\']\s*$')

def normalize_text(text):
    text = text.replace(r'\"', '"')
    text = text.replace(r"\'", "'")
    return text

def run():
    #test_input = StringIO.StringIO()
    #test_input.write('\n'.join(src))
    global src  # pylint: disable=global-statement
    global dest # pylint: disable=global-statement
    src = {int(k) : v for k, v in src.items()}
    dest = {int(k) : v for k, v in dest.items()}
    src_keys = sorted(src)
    test_input = '\n'.join([src[_] for _ in src_keys])

    print('running anonymize tests using: {} {}'.format(anonymize, args))
    cmd = [anonymize] + args.split()
    process = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE)
    # encode as bytes for Python 3 :-/
    test_input = str.encode(test_input, 'utf-8')
    (stdout, _) = process.communicate(input=test_input)
    index = 0
    # convert bytes to string
    stdout = stdout.decode("utf-8")
    # pylint: disable=redefined-outer-name
    for line in stdout.split('\n'):
        key = src_keys[index]
        _input = src[key]
        expected = dest[key]
        if line != expected:
            print('FAILED to anonymize line during test {}'.format(key))
            print('input:    {}'.format(_input))
            print('expected: {}'.format(expected))
            print('got:      {}'.format(line))
            sys.exit(1)
        print('SUCCEEDED anonymization test {}'.format(key))
        index += 1

with open(anonymize_test_sh) as filehandle:
    for line in filehandle:
        src_match = src_regex.match(line)
        if src_match:
            key = src_match.group(1)
            if key in src:
                raise AssertionError('Duplicate key index src[{}]'.format(key))
            value = src_match.group(2)
            value = normalize_text(value)
            src[key] = value
        dest_match = dest_regex.match(line)
        if dest_match:
            key = dest_match.group(1)
            if key in dest:
                raise AssertionError('Duplicate key index dest[{}]'.format(key))
            value = dest_match.group(2)
            value = normalize_text(value)
            dest[key] = value
        args_match = args_regex.match(line)
        if args_match:
            args = args_match.group(1)
            run()
            src = {}
            dest = {}

"""Tests for the `scmtiles.config.get_arg_handler` function."""
# Copyright 2016 Andrew Dawson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from contextlib import redirect_stderr
from io import StringIO
import sys
import unittest

from scmtiles.cli import get_arg_handler
from scmtiles.exceptions import CLIError, CLIHelp


class Test(unittest.TestCase):

    def test_valid(self):
        parser = get_arg_handler()
        args = ['path/to/my_config_file.cfg']
        argns = parser.parse_args(args)
        self.assertEqual(argns.config_file_path, args[0])

    def test_help(self):
        parser = get_arg_handler()
        args = ['-h']
        with self.assertRaises(CLIHelp):
            argns = parser.parse_args(args)

    def test_no_args(self):
        parser = get_arg_handler()
        args = []
        error_message = ('the following arguments are required: '
                         'config_file_path')
        with self.assertRaisesRegex(CLIError, error_message):
            with redirect_stderr(StringIO()):
                argns = parser.parse_args(args)

    def test_too_many_args(self):
        parser = get_arg_handler()
        args = ['one', 'two']
        error_message = 'unrecognized arguments: two'
        with self.assertRaisesRegex(CLIError, error_message):
            with redirect_stderr(StringIO()):
                argns = parser.parse_args(args)
                print(argns)

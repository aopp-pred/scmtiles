"""Command line interface tools for the SCM Tiles software."""
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

from argparse import ArgumentParser
import sys

from .exceptions import CLIError, CLIHelp


class _NonExitingArgumentParser(ArgumentParser):
    """Subclass of `ArgumentParser` that won't exit a program."""

    def error(self, message):
        """
        Override how errors in argument parsing are handled. This just
        prints the program usage as normal then raises a `CLIError`
        exception which can be handled by the caller.

        """
        self.print_usage(file=sys.stderr)
        sys.stderr.flush()
        raise CLIError(message)

    def exit(self):
        """
        Override the exit method of the parser, in this case just raise
        a `CLIHelp` exception which can be handled by the caller.

        """
        raise CLIHelp()


def get_arg_handler():
    """"""
    parser = _NonExitingArgumentParser()
    parser.add_argument(
        'config_file_path',
        type=str,
        help='path to the program configuration file')
    return parser

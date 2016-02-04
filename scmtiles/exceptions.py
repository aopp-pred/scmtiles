"""Custom exceptions for the SCM Tiles software."""
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


class CLIError(Exception):
    """Command line argument error."""
    pass


class CLIHelp(Exception):
    """Raised when the CLI wants to show help and exit."""
    pass


class ConfigurationError(Exception):
    """A general configuration input error."""
    pass


class TileInitializationError(Exception):
    """An error initializing a tile."""
    pass


class TileRunError(Exception):
    """An error running a tile."""
    pass

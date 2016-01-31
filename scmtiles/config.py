"""Configuration of the SCM Tiles software."""
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

import os
from collections import namedtuple
from configparser import (ConfigParser, ExtendedInterpolation,
                          NoSectionError, NoOptionError)
from dateutil.parser import parse as parse_date

from .exceptions import ConfigurationError


def _to_path(s):
    return os.path.expandvars(os.path.expanduser(str(s)))


class SCMTilesConfig(object):
    """A configuration object for the SCM Tiles software."""

    # Sections of the configuration file and the options they should contain.
    _config_template = {'default': (('start_time', parse_date),
                                    ('gridx', int),
                                    ('gridy', int),
                                    ('input_directory', _to_path),
                                    ('output_directory', _to_path),
                                    ('work_directory', _to_path),
                                    ('template_directory', _to_path))}

    def __init__(self, start_time, gridx, gridy, input_directory,
                 output_directory, work_directory, template_directory,
                 strict=True):
        """
        Create an `SCMTilesConfig` object by specifying configuration
        items.

        Configuration objects are usually created using the `from_file`
        static method rather than being initialized directly.

        """
        self.start_time = start_time
        # Grid must have positive sizes in x and y directions.
        if strict and (gridx <= 0 or gridy <= 0):
            msg = 'Grid sizes must be >= 1, got gridx={} and gridy={}.'
            raise ConfigurationError(msg.format(gridx, gridy))
        self.gridx = gridx
        self.gridy = gridy
        # The input and template directories are required to exist, the output
        # and work directories may be able to be created when required.
        if strict and not os.path.exists(input_directory):
            msg = 'The input directory "{}" does not exist.'
            raise ConfigurationError(msg.format(input_directory))
        self.input_directory = input_directory
        if strict and not os.path.exists(template_directory):
            msg = 'The template directory "{}" does not exist.'
            raise ConfigurationError(msg.format(template_directory))
        self.template_directory = template_directory
        self.work_directory = work_directory
        self.output_directory = output_directory

    @staticmethod
    def from_file(config_file_path, strict=True):
        """Create an `SCMTilesConfig` from a configuration file.

        **Argument:**

        * config_file_path
            The path to the configuration file to be loaded.

        **Returns:**

        * config
            An `SCMTilesConfig` object.

        """
        config = ConfigParser()
        files_loaded = config.read(config_file_path)
        if not files_loaded:
            msg = ('The configuration file "{}" does not exist '
                   'or is not readable.')
            raise ConfigurationError(msg.format(config_file_path))
        config_args = {}
        for section in SCMTilesConfig._config_template.keys():
            for option, ctype in SCMTilesConfig._config_template[section]:
                try:
                    config_args[option] = ctype(config.get(section, option))
                except NoSectionError:
                    msg = 'Missing section "[{}]" in configuration file "{}"'
                    raise ConfigurationError(msg.format(section,
                                                        config_file_path))
                except NoOptionError:
                    msg = ('Configuration option "{}" is missing from '
                           'section "[{}]" in file "{}".')
                    raise ConfigurationError(msg.format(option,
                                                        section,
                                                        config_file_path))
                except ValueError:
                    msg = ('Cannot convert option "{}" to the required '
                           'type "{!r}"')
                    raise ConfigurationError(msg.format(option, ctype))
        return SCMTilesConfig(**config_args, strict=strict)

    def __str__(self):
        fmt = ('SCMTilesConfig(start_time="{x.start_time}", '
               'gridx={x.gridx}, '
               'gridy={x.gridy}, '
               'input_directory="{x.input_directory}", '
               'output_directory="{x.output_directory}", '
               'work_directory="{x.work_directory}", '
               'template_directory="{x.template_directory}")')
        return fmt.format(x=self)

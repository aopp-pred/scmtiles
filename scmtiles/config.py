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

from collections import namedtuple
from configparser import ConfigParser, NoSectionError, NoOptionError

from .exceptions import ConfigurationError


#: A configuration object for the SCM Tiles software.
SCMTilesConfig = namedtuple('SCMTilesConfig', ('gridx',
                                               'gridy',
                                               'input_directory',
                                               'output_directory',
                                               'work_directory',
                                               'template_directory'))


# Sections of the configuration file and the options they should contain.
_CONFIG_TEMPLATE = {'grid': (('gridx', int), ('gridy', int)),
                    'io': (('input_directory', str),
                           ('output_directory', str),
                           ('work_directory', str),
                           ('template_directory', str))}


def read_config(config_file_path):
    """Read an SCM Tiles configuration file.

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
    for section in _CONFIG_TEMPLATE.keys():
        for option, ctype in _CONFIG_TEMPLATE[section]:
            try:
                config_args[option] = ctype(config.get(section, option))
            except NoSectionError:
                msg = 'Missing section "[{}]" in configuration file "{}"'
                raise ConfigurationError(msg.format(section, config_file_path))
            except NoOptionError:
                msg = ('Configuration option "{}" is missing from '
                       'section "[{}]" in file "{}".')
                raise ConfigurationError(msg.format(option,
                                                    section,
                                                    config_file_path))
            except ValueError:
                msg = 'Cannot convert option "{}" to the required type "{!r}"'
                raise ConfigurationError(msg.format(option, ctype))
    return SCMTilesConfig(**config_args)

"""Tests for the `scmtiles.config.SCMTilesConfig` class."""
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

from collections import OrderedDict
from datetime import datetime
from tempfile import NamedTemporaryFile
import unittest

from scmtiles.config import SCMTilesConfig
from scmtiles.exceptions import ConfigurationError


class Test_from_file(unittest.TestCase):

    def setUp(self):
        self.config_dict = OrderedDict(
            start_time=datetime(2009, 4, 6, 1, 15),
            forcing_step_seconds=900,
            forcing_num_steps=3,
            xname='lon',
            yname='lat',
            gridx=480,
            gridy=142,
            input_directory='/tmp',
            output_directory='/tmp',
            work_directory='/tmp',
            template_directory='/tmp',
            input_file_pattern='scm_in.2009-04-06T01:15:00.nc')

    def _config_from_dict(self, config_dict, section_name='[default]'):
        config_pairs = ["{!s} = {!s}".format(key, value)
                        for (key, value) in config_dict.items()]
        config_text = "{!s}\n{!s}".format(section_name,
                                            "\n".join(config_pairs))
        return config_text

    def _check_exception(self, config_text, exception_class, error_message):
        with NamedTemporaryFile(mode='w', buffering=1) as fp:
            config_file_path = fp.name
            with open(config_file_path, 'w') as cf:
                cf.write(config_text)
            error_regex = error_message.format(config_file_path)
            with self.assertRaisesRegex(exception_class, error_regex):
                config = SCMTilesConfig.from_file(config_file_path)

    def test_valid(self):
        expected_config = self.config_dict
        config_text = self._config_from_dict(expected_config)
        with NamedTemporaryFile(mode='w', buffering=1) as fp:
            config_file_path = fp.name
            with open(config_file_path, 'w') as cf:
                cf.write(config_text)
            config = SCMTilesConfig.from_file(config_file_path)
            for key in expected_config.keys():
                self.assertEqual(getattr(config, key), expected_config[key])

    def test_unreadable(self):
        # NB: one assumes this file won't exist.
        bad_file = '/scmtiles.cfg'
        error_message = ('The configuration file "{}" does not exist '
                         'or is not readable.'.format(bad_file))
        with self.assertRaisesRegex(ConfigurationError, error_message):
            config = SCMTilesConfig.from_file(bad_file)

    def test_missing_section(self):
        config_dict = self.config_dict
        config_text = self._config_from_dict(config_dict, section_name='')
        error_message = ('The configuration file "{}" is not valid, it '
                         'must contain a section header.')
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_missing_default_section(self):
        config_dict = self.config_dict
        config_text = self._config_from_dict(config_dict, section_name='[a]')
        error_message = ('Missing section "\[default\]" in configuration '
                         'file "{}".')
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_missing_option(self):
        config_dict = self.config_dict
        del config_dict['start_time']
        config_text = self._config_from_dict(config_dict)
        error_message = ('Configuration option "start_time" is missing '
                         'from section "\[default\]" in file "{}".')
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_from_file_bad_time_type(self):
        config_dict = self.config_dict
        config_dict['start_time'] = 'not a time or date'
        config_text = self._config_from_dict(config_dict)
        error_message = ('Cannot convert option "start_time" to the required '
                         'type ".*".')
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_from_file_bad_grid_size_non_integer(self):
        config_dict = self.config_dict
        config_dict['gridx'] = 'seven'
        config_text = self._config_from_dict(config_dict)
        error_message = ('Cannot convert option "gridx" to the required '
                         'type ".*".')
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_from_file_bad_grid_size_invalid(self):
        config_dict = self.config_dict
        config_dict['gridx'] = 0
        config_text = self._config_from_dict(config_dict)
        error_message = ('Grid sizes must be >= 1, got gridx={} and gridy={}.'
                         ''.format(config_dict['gridx'], config_dict['gridy']))
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_input_directory_does_not_exist(self):
        config_dict = self.config_dict
        config_dict['input_directory'] = '/scmtiles_input'
        config_text = self._config_from_dict(config_dict)
        error_message = ('The input directory "{}" does not exist.'
                         ''.format(config_dict['input_directory']))
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_template_directory_does_not_exist(self):
        config_dict = self.config_dict
        config_dict['template_directory'] = '/scmtiles_template'
        config_text = self._config_from_dict(config_dict)
        error_message = ('The template directory "{}" does not exist.'
                         ''.format(config_dict['template_directory']))
        self._check_exception(config_text, ConfigurationError, error_message)

    def test_from_file_non_strict(self):
        config_dict = self.config_dict
        config_dict['gridx'] = 0
        config_dict['input_directory'] = '/scmtiles_input'
        config_dict['template_directory'] = '/scmtiles_template'
        config_text = self._config_from_dict(config_dict)
        with NamedTemporaryFile(mode='w', buffering=1) as fp:
            config_file_path = fp.name
            with open(config_file_path, 'w') as cf:
                cf.write(config_text)
            config = SCMTilesConfig.from_file(config_file_path, strict=False)
            for key in ('gridx', 'input_directory', 'template_directory'):
                self.assertEqual(getattr(config, key), config_dict[key])

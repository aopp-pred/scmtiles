"""Integration test using a simple dummy model definition."""
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

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import os
from os.path import join as pjoin
import shutil
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
import unittest

from scmtiles.task import TileTask
from scmtiles.runner import TileRunner, CellResult
from scmtiles.test import _get_test_data_path


class SimpleRunner(TileRunner):
    """
    A simple implementation of a `TileRunner` class that doesn't do much
    other than write an input file and an output file.

    """

    def run_cell(self, cell, logger):
        """Run the model for the given cell."""
        # Create a run directory and create links to the template.
        run_directory = self.create_run_directory()
        self.link_template(run_directory)
        # Write the input netcdf file.
        cell_ds = self.get_cell(cell)
        cell_ds.to_netcdf(pjoin(run_directory, 'input.nc'))
        # Simulate a model doing somthing by writing an output text file
        # consisting of the xarray representation of the input dataset and
        # the single required input file.
        output_file = pjoin(run_directory, 'output.txt')
        with open(output_file, 'w') as fh:
            fh.write('{!s}\n'.format(cell_ds))
            with open(pjoin(run_directory, 'required.txt'), 'r') as rh:
                fh.write(rh.read())
        # Archive the run output to the output direcrtory.
        outputs = self.archive_output(cell, run_directory)
        return CellResult(cell, outputs)

    def archive_output(self, cell, run_directory):
        """Archive the model output."""
        # Construct an output file path including the run start time and
        # the cell's location in the full grid.
        time_portion = self.config.start_time.strftime('%Y%m')
        grid_portion = 'y{:02d}x{:02d}'.format(cell.y_global, cell.x_global)
        archive_file_name = 'output.{!s}.{!s}.txt'.format(time_portion,
                                                          grid_portion)
        archive_file_path = pjoin(self.config.output_directory,
                                  archive_file_name)
        # Move the model output file to the output directory.
        shutil.move(pjoin(run_directory, 'output.txt'), archive_file_path)
        return [archive_file_path]


#: A string template for an SCM Tiles configuration file, to be filled
#: in using string formatting.
_CONFIG_TEMPLATE = """
[default]

start_time = 2016-01-01T00:00:00
forcing_step_seconds = 1
forcing_num_steps = 0

xname = lon
yname = lat
gridx = 28
gridy = 6

input_directory = {input_directory:s}
template_directory = {template_directory:s}
work_directory = {work_directory:s}
output_directory = {output_directory:s}
input_file_pattern = grid.{{start_time.year:04d}}{{start_time.month:02d}}.nc
"""


class Test_SimpleRunner(unittest.TestCase):

    def setUp(self):
        # Create the run sandbox in the user's home directory.
        self.sandbox_dir = TemporaryDirectory(dir=os.path.expanduser('~'),
                                              prefix='scmtiles.test_simple.')
        base_path = self.sandbox_dir.name
        self.input_directory = pjoin(base_path, 'inputs')
        self.template_directory = pjoin(base_path, 'template')
        self.work_directory = pjoin(base_path, 'work')
        self.output_directory = pjoin(base_path, 'run')
        os.mkdir(self.input_directory)
        os.mkdir(self.template_directory)
        os.mkdir(self.work_directory)
        os.mkdir(self.output_directory)
        # Symlink the reference input file.
        os.symlink(_get_test_data_path('grid.201601.nc'),
                   pjoin(self.input_directory, 'grid.201601.nc'))
        # Create a dummy template.
        with open(pjoin(self.template_directory, 'required.txt'), 'w') as f:
            f.write('This file is needed for a run.')

    def tearDown(self):
        # Delete the sandbox directory.
        self.sandbox_dir.cleanup()

    def write_config_file(self):
        # Write a configuration file in /tmp.
        config_text = _CONFIG_TEMPLATE.format(
            input_directory=self.input_directory,
            template_directory=self.template_directory,
            work_directory=self.work_directory,
            output_directory=self.output_directory,
        )
        config_file = NamedTemporaryFile(mode='w', buffering=1)
        config_file.write(config_text)
        return config_file

    def verify_run(self):
        # Verify that all the expected output files were written, and that
        # they contain the expected information.
        for y in range(6):
            for x in range(28):
                filename = pjoin(self.output_directory,
                                 'output.201601.y{:02d}x{:02d}.txt'
                                 ''.format(y, x))
                # The expected output file must exist.
                self.assertTrue(os.path.exists(filename))
                # The file should contain a dataset description and the line
                # from required.txt. Check that the number of lines is > 2,
                # which is a crude way of checking there is something else in
                # the file other than the contents of required.txt. Then check
                # That the specific text from required.txt is present.
                with open(filename, 'r') as fh:
                    lines = fh.readlines()
                self.assertTrue(len(lines) > 2)
                self.assertTrue('This file is needed for a run.' in lines)

    def test_rows(self):
        config_file = self.write_config_file()
        cliargs = ['simple', config_file.name]
        task = TileTask(SimpleRunner, decompose_mode='rows')
        # Catch both stdout and stderr while doing this.
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            task.initialize(cliargs=cliargs)
            task.run()
            status = task.finalize()
        # Close the config file object which deletes it.
        config_file.close()
        self.assertEqual(status, 0)
        self.verify_run()

    def test_cells(self):
        config_file = self.write_config_file()
        cliargs = ['simple', config_file.name]
        task = TileTask(SimpleRunner, decompose_mode='cells')
        # Catch both stdout and stderr while doing this.
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            task.initialize(cliargs=cliargs)
            task.run()
            status = task.finalize()
        # Close the config file object which deletes it.
        config_file.close()
        self.assertEqual(status, 0)
        self.verify_run()

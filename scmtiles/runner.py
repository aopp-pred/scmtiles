"""Model independent definitions for running models."""
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
from datetime import timedelta
from os.path import join as pjoin
from tempfile import mkdtemp

import xray as xr

from .exceptions import TileInitializationError
from .util import get_logger


#: The result of a single cell simulation.
CellResult = namedtuple('CellResult', ('cell', 'outputs'))

#: The result of a whole tile of simulations.
TileResult = namedtuple('TileResult', ('id', 'cell_results'))


class TileRunner(object):

    def __init__(self, config, tile, tile_in_memory=True):
        self.config = config
        self.tile = tile
        self._tile_data = self._load_tile_data(in_memory=tile_in_memory)

    def _load_tile_data(self, in_memory=True):
        selector = {self.config.xname: self.tile.xselector,
                    self.config.yname: self.tile.yselector}
        # Add new configuration items forcing_step_seconds and
        # forcing_num_steps which can be used to gather the correct input times
        forcing_length = self.config.forcing_num_steps * \
            self.config.forcing_step_seconds
        forcing_leads = range(0, forcing_length + 1,
                              self.config.forcing_step_seconds)
        forcing_times = [self.config.start_time + timedelta(seconds=n)
                         for n in forcing_leads]
        input_file_names = [self.config.input_file_pattern.format(
                                tile=self.tile, start_time=t)
                            for t in forcing_times]
        input_file_paths = [pjoin(self.config.input_directory, f)
                            for f in input_file_names]
        try:
            with xr.open_mfdataset(input_file_paths) as ds:
                tile_ds = ds.isel(**selector)
                if in_memory:
                    tile_ds.load()
        except RuntimeError:
            msg = 'Failed to open input file "{}".'
            raise TileInitializationError(msg.format(input_file_path))
        return tile_ds

    def get_cell(self, cell):
        selector = {self.config.xname: cell.x, self.config.yname: cell.y}
        return self._tile_data.isel(**selector)

    def create_run_directory(self):
        """
        Create a temporary run directory.

        **Returns:**

        * run_directory
            The path to the created directory.

        """
        try:
            run_directory = mkdtemp(dir=self.config.work_directory,
                                    prefix='run.')
        except PermissionError:
            msg = 'Cannot create run directory "{}", permission denied.'
            raise TileRunError(msg.format(run_directory))
        return run_directory

    def run_cell(self, cell, logger=print):
        raise NotImplementedError('run_cell() must be defined.')

    def run(self):
        """Start the SCM runs in serial."""
        log_file_name = 'run.{:03d}.{}.log'.format(
            self.tile.id, self.config.start_time.strftime('%Y%m%d%H%M%S'))
        log_file_path = pjoin(self.config.work_directory, log_file_name)
        with open(log_file_path, 'w') as lf:
            # Write a header to the run log file.
            header = ('Tile #{d.id:03d}: '
                      'x=[{d.xselector.start}, {d.xselector.stop}), '
                      'y=[{d.yselector.start}, {d.yselector.stop})\n')
            lf.write(header.format(d=self.tile))
            log = get_logger(lf)
            tile_result = TileResult(id=self.tile.id, cell_results=[])
            for cell in self.tile.cells():
                cell_result = self.run_cell(cell, logger=log)
                tile_result.cell_results.append(cell_result)
            log('Finished tile #{:03d}'.format(self.tile.id))
        return tile_result

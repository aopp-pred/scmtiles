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

from abc import ABCMeta, abstractmethod
from collections import namedtuple
from datetime import timedelta
import glob
import os
from os.path import join as pjoin
from tempfile import mkdtemp

import xray as xr

from .exceptions import TileInitializationError, TileRunError
from .util import get_logger


#: The result of a single cell simulation.
CellResult = namedtuple('CellResult', ('cell', 'outputs'))

#: The result of a whole tile of simulations.
TileResult = namedtuple('TileResult', ('id', 'cell_results'))


class TileRunner(metaclass=ABCMeta):

    def __init__(self, config, tile, tile_in_memory=True):
        """
        Construct a tile runner.

        **Arguments:**

        * config: `scmtiles.config.SCMTilesConfig`
            A configuration object defining the parameters for the tile.

        * tile: `scmtiles.grid_manager.Tile`
            A tile defining the work required of the runner.

        **Optional argument:**

        * tile_in_memory
            If `True` then the data for the tile will be loaded from
            file into memory at initialization time. If `False` then
            data from the file will be read as needed from the file.
            Defaults to `True`.

        """
        self.config = config
        self.tile = tile
        self._tile_data = self._load_tile_data(in_memory=tile_in_memory)

    def _load_tile_data(self, in_memory=True):
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
        # Define the tile selector.
        if self.tile.type == 'linear':
            selector = {'grid': self.tile.selector}
        else:
            selector = {self.config.xname: self.tile.xselector,
                        self.config.yname: self.tile.yselector}
        try:
            with xr.open_mfdataset(input_file_paths) as ds:
                if self.tile.type == 'linear':
                    # Reconfigure the grid for linear tiles.
                    ds = ds.stack(grid=(self.config.yname, self.config.xname))
                tile_ds = ds.isel(**selector)
                if in_memory:
                    tile_ds.load()
        except RuntimeError:
            msg = 'Failed to open input files "{}".'
            raise TileInitializationError(msg.format(input_file_paths))
        except ValueError:
            msg = 'Failed to select input tile, check grid dimension names'
            raise TileInitializationError(msg)
        return tile_ds

    def run(self):
        """Start the tile's runs in serial."""
        log_file_name = 'run.{:03d}.{}.log'.format(
            self.tile.id, self.config.start_time.strftime('%Y%m%d%H%M%S'))
        log_file_path = pjoin(self.config.work_directory, log_file_name)
        # Create the work directory if it doesn't exist.
        try:
            os.makedirs(self.config.work_directory, exist_ok=True)
        except PermissionError as e:
            msg = 'Cannot create work directory "{}", permission denied.'
            raise TileRunError(msg.format(run_directory))
        with open(log_file_path, 'w') as lf:
            # Write a header to the run log file.
            header = 'Tile: {!s}`n'.format(self.tile)
            lf.write(header)
            log = get_logger(lf)
            tile_result = TileResult(id=self.tile.id, cell_results=[])
            for cell in self.tile.cells():
                cell_result = self.run_cell(cell, logger=log)
                tile_result.cell_results.append(cell_result)
            log('Finished tile #{:03d}'.format(self.tile.id))
        return tile_result

    @abstractmethod
    def run_cell(self, cell, logger=print):
        """
        Run an individual cell of the tile.

        **Argument:**

        * cell
            A `Cell` instance des cribing the cell to be run.

        **Keyword argument:**

        * logger
            A callable logging function. Defaults to `print`.

        **Returns:**

        * cell_result
            A `CellResult` object describing the result of the run.

        .. note:: This method must be implemented by the derived class.

        """
        raise NotImplementedError('run_cell() must be defined.')

    def get_cell(self, cell):
        """
        Retrieve the `xarray.Dataset` corresponding to a given cell
        belonging to the tile.

        **Arguments:**

        * cell: `scmtiles.grid_manager.Cell`
            The cell to extract from the tile.

        **Returns:**

        * cell_ds: `xarray.Dataset`
            The dataset corresponding to the required cell.

        """
        if self.tile.type == 'linear':
            selector = {'grid': cell.x}
        else:
            selector = {self.config.xname: cell.x, self.config.yname: cell.y}
        cell_ds = self._tile_data.isel(**selector)
        if self.tile.type == 'linear':
            # Convert the grid coordinate back to latitude and longitude.
            # NB: cell_ds.unstack('grid') does not appear to work.
            lat, lon = cell_ds['grid'].data
            cell_ds.coords.update({self.config.yname: lat,
                                   self.config.xname: lon})
            cell_ds = cell_ds.drop('grid')
        return cell_ds

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

    def link_template(self, run_directory):
        """
        Link all filesin the template directory to the run directory.

        **Argument:**

        * run_directory
            Path to the run directory in which links will be created.

        **Returns:**

        * linked_files
            A list of 2-tuples containing the full paths to the source
            and target of each linked file.

        """
        linked_files = []
        template_pattern = '{}/*'.format(self.config.template_directory)
        for source in glob.glob(template_pattern):
            target = pjoin(run_directory, os.path.basename(source))
            try:
                os.symlink(source, target)
            except PermissionError:
                msg = 'Cannot create links in "{}", permission denied.'
                raise TileRunError(msg.format(run_directory))
            else:
                linked_files.append((source, target))
        return linked_files

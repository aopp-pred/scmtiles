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
import logging
import os
from os.path import join as pjoin
import re
from tempfile import mkdtemp

import xarray as xr

from .exceptions import TileInitializationError, TileRunError


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
        self.tile_ds = self._load_tile_data(in_memory=tile_in_memory)

    def _load_tile_data(self, in_memory=True):
        # Add new configuration items forcing_step_seconds and
        # forcing_num_steps which can be used to gather the correct input times
        forcing_length = self.config.forcing_num_steps * \
            self.config.forcing_step_seconds
        forcing_leads = range(0, forcing_length,
                              self.config.forcing_step_seconds)
        forcing_times = [self.config.start_time + timedelta(seconds=n)
                         for n in forcing_leads]
        input_file_names = [self.config.input_file_pattern.format(time=t)
                            for t in forcing_times]
        input_file_paths = [pjoin(self.config.input_directory, f)
                            for f in input_file_names]
        try:
            ds = xr.open_mfdataset(input_file_paths)
            if self.tile.type == 'linear':
                # Reconfigure the grid for linear tiles.
                chunks = {'grid': len(ds[self.config.xname])}
                ds = ds.stack(grid=(self.config.yname, self.config.xname))
                selector = {'grid': self.tile.selector}
            else:
                chunks = {self.config.yname: (self.tile.yselector.stop -
                                              self.tile.yselector.start)}
                selector = {self.config.xname: self.tile.xselector,
                            self.config.yname: self.tile.yselector}
            tile_ds = ds.chunk(chunks).isel(**selector)
            if in_memory:
                tile_ds.load()
        except RuntimeError as e:
            msg = 'Failed to open input files "{}": {!s}'
            raise TileInitializationError(msg.format(input_file_paths, e))
        except ValueError as e:
            if 'concat_dim' in str(e):
                msg = ("Failed to load input tiles, couldn't concatenate"
                       "over time dimension, is it single-valued?")
            elif re.match(r'dimensions \[.*\] do not exist', str(e)):
                msg = ("Failed to select input tile, check grid dimensions "
                       "in configuration match those in the files")
            else:
                msg = "An error occurred while reading input tiles: {!s}"
            raise TileInitializationError(msg.format(e))
        return tile_ds

    def run(self, parent_logger):
        """Start the tile's runs in serial."""
        # Create a logger for this tile:
        logger = logging.getLogger(name='{}:tile{:03d}'.format(
            parent_logger, self.tile.id))
        logger.setLevel(logging.DEBUG)
        log_file_name = 'run.{:03d}.{}.log'.format(
            self.tile.id, self.config.start_time.strftime('%Y%m%d%H%M%S'))
        log_file_path = pjoin(self.config.output_directory, log_file_name)
        try:
            log_handler = logging.FileHandler(log_file_path)
        except PermissionError:
            msg = 'Cannot write to the output directory: {}'
            raise TileRunError(msg.format(self.config.output_directory))
        log_handler.setLevel(logging.DEBUG)
        log_name = 'tile #{:03d}'.format(self.tile.id)
        log_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] ({}) %(levelname)s %(message)s'.format(log_name),
            datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(log_handler)
        # Write a message to the main log giving the location of this tile's
        # log file:
        base_logger = logging.getLogger(parent_logger)
        base_logger.info('Logging tile #{:03d} to: {}'.format(
            self.tile.id, log_file_path))
        # Run each cell in the tile:
        logger.info('Run started'.format(self.tile.id))
        tile_result = TileResult(id=self.tile.id, cell_results=[])
        for cell in self.tile.cells():
            cell_result = self.run_cell(cell, logger=logger)
            tile_result.cell_results.append(cell_result)
        logger.info('Finished running tile')
        log_handler.close()
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
        cell_ds = self.tile_ds.isel(**selector)
        if self.tile.type == 'linear':
            # Convert the grid coordinate back to latitude and longitude.
            # NB: cell_ds.unstack('grid') does not appear to work.
            lat, lon = cell_ds['grid'].values.tolist()
            cell_ds.coords.update({self.config.yname: lat,
                                   self.config.xname: lon})
            cell_ds = cell_ds.drop_vars('grid')
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
        except (OSError, PermissionError):
            msg = 'Cannot create run directory in "{}".'
            raise TileRunError(msg.format(self.config.work_directory))
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

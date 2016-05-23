"""Task definitions for running tiles in parallel."""
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

import inspect
import logging
import os
import sys
import time

from mpi4py import MPI

from .cli import get_arg_handler
from .config import SCMTilesConfig
from .exceptions import (CLIError, CLIHelp, ConfigurationError,
                         TileInitializationError, TileRunError)
from .grid_manager import GridManager
from ._version import __version__ as scmtiles_version


class TileTask(object):
    """A single task."""

    #: Rank of the master task, always 0.
    MASTER = 0

    #: Set up a logger for all tasks to share.
    logger = logging.getLogger(name='all_tasks')
    logger.setLevel(logging.DEBUG)
    log_handler = logging.StreamHandler()
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] (%(name)s) %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(log_handler)

    def __init__(self, runner_class, runner_kwargs=None,
                 decompose_mode='rows'):
        """Create an SCM Tiles task."""
        # Define an MPI communicator.
        self.comm = MPI.COMM_WORLD
        # Determine if this task is the master task.
        self.rank = self.comm.rank
        self.is_master = self.rank == 0
        # Set default null values for domain and config instance variables.
        self.tile = None
        self.config = None
        # The class used to construct tile runners.
        self.runner_class = runner_class
        self.runner_kwargs = runner_kwargs or {}
        self.decompose_mode = decompose_mode

    def initialize(self, cliargs=None):
        """
        Initialize the task, setting the domain and configuration.

        """
        if self.is_master:
            # Master task handles command line arguments and distributes
            # the configuration to all workers, as well as assigning a domain
            # for each worker.
            try:
                if cliargs is None:
                    cliargs = sys.argv
                args = get_arg_handler().parse_args(cliargs[1:])
                # Do some logging, these details are helpful for reproducing
                # experiments:
                self.logger.info('Running {}'.format(os.path.abspath(cliargs[0])))
                self.logger.info('Backend scmtiles is version {}'.format(
                    scmtiles_version))
                runner_name = self.runner_class.__name__
                runner_module = inspect.getfile(self.runner_class)
                runner_version = getattr(self.runner_class,
                                         '__version__',
                                         '<unknown>')
                runner_msg = ('Tile runner class is {} from module {} '
                              'at version {}')
                self.logger.info(runner_msg.format(
                    runner_name, runner_module, runner_version))
                # Load the program configuration file:
                config = SCMTilesConfig.from_file(args.config_file_path)
                self.logger.info(
                    'Configuration file loaded successfully: {}'.format(
                        os.path.abspath(args.config_file_path)))
                self.logger.info('Configuration is: {!s}'.format(config))
                if not os.path.exists(config.output_directory):
                    os.makedirs(config.output_directory)
                    msg = 'Created output directory: {}'
                    self.logger.info(msg.format(config.output_directory))
            except CLIError as e:
                # An error was detected in the command line arguments. Print
                # the error message to stderr and make sure all processes exit
                # with status 1.
                print(str(e), file=sys.stderr, flush=True)
                self.comm.bcast((True, 1), root=TileTask.MASTER)
                sys.exit(1)
            except ConfigurationError as e:
                # An error was detected either in the parsing of the
                # configuration file. Log the error and make sure all
                # processes exit with code 1.
                self.logger.critical(str(e))
                self.comm.bcast((True, 1), root=TileTask.MASTER)
                sys.exit(1)
            except CLIHelp:
                # CLIHelp is raised when the program was run with the help
                # option, which should exit with code 0 once the help is
                # printed to the screen.
                self.comm.bcast((True, 0), root=TileTask.MASTER)
                sys.exit(0)
            except PermissionError:
                # If creating the output directory failed then exit with an
                # error message.
                msg = 'Cannot create output directory, permission denied: {}'
                self.logger.critical(msg.format(config.output_directory))
                self.comm.bcast((True, 2), root=TileTask.MASTER)
                sys.exit(2)
            else:
                # Broadcast a no error message to all processes.
                self.comm.bcast((False, None), root=TileTask.MASTER)
            num_processes = self.comm.size
            gm = GridManager(config.xsize, config.ysize, num_processes)
            if self.decompose_mode == 'cells':
                tiles = gm.decompose_by_cells()
            else:
                tiles = gm.decompose_by_rows()
            self.logger.info(
                'Domain tiled for {} processes'.format(num_processes))
        else:
            # Receive an error package from the master process, if an error
            # condition has been encountered by the master process then exit
            # with the provided exit code.
            error, stat = self.comm.bcast(None, root=TileTask.MASTER)
            if error:
                sys.exit(stat)
            # Worker tasks will be given the appropriate configuration and
            # domain objects.
            tiles = None
            config = None
        # Use an MPI broadcast to send the configuration object to all tasks.
        self.config = self.comm.bcast(config, root=TileTask.MASTER)
        # Use an MPI scatter to send one domain to each task.
        self.tile = self.comm.scatter(tiles, root=TileTask.MASTER)
        if self.is_master:
            self.logger.info('Initialization complete')

    def run(self):
        """Run each task."""
        # Create a tile runner and run all the jobs for the tile.
        if self.is_master:
            self.logger.info('Running tiles')
        try:
            if self.tile is not None:
                runner = self.runner_class(self.config, self.tile,
                                           **self.runner_kwargs)
        except TileInitializationError as e:
            msg = 'Runner for tile #{:03d} failed to initialize: {!s}'
            self.logger.error(msg.format(self.tile.id, e))
            run_info = None
        else:
            if self.tile is not None:
                try:
                    run_info = runner.run()
                except TileRunError as e:
                    msg = 'Tile #{:03d} failed to run: {!s}'
                    self.logger.error(msg.format(self.tile.id, e))
                    run_info = None
            else:
                run_info = None
        # Use an MPI gather call to wait for each process to finish.
        self.run_info = self.comm.gather(run_info, root=TileTask.MASTER)
        if self.is_master:
            self.logger.info('All tiles have completed running')

    def finalize(self):
        if not self.is_master:
            # Only the master needs to finalize.
            return 0
        self.logger.info('Performing finalization checks')
        # Inspect run_info to determine if any of the tiles failed.
        status = 0
        for tile_result in self.run_info:
            if tile_result is None:
                # Tiles that failed to run have no information.
                continue
            if any([cr.outputs is None for cr in tile_result.cell_results]):
                msg = 'Tile #{:03d} had failed cells'
                self.logger.error(msg.format(tile_result.id))
                for cell_result in tile_result.cell_results:
                    if cell_result.outputs is None:
                        status += 1
                        msg = '- Failed cell: {!s}'
                        self.logger.error(msg.format(cell_result.cell))
                sys.stderr.flush()
        self.logger.info('Run complete (status = {})'.format(status))
        return status

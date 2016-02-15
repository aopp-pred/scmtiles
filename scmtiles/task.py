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

import os
import sys
import time

from mpi4py import MPI

from .cli import get_arg_handler
from .config import SCMTilesConfig
from .exceptions import (CLIError, CLIHelp, ConfigurationError,
                         TileInitializationError, TileRunError)
from .grid_manager import GridManager


class TileTask(object):
    """A single task."""

    #: Rank of the master task, always 0.
    MASTER = 0

    def __init__(self, runner_class, decompose_mode='rows'):
        """Create an SCM Tiles task."""
        # Define an MPI communicator.
        self.comm = MPI.COMM_WORLD
        # Determine if this task is the master task.
        self.rank = self.comm.Get_rank()
        self.is_master = self.rank == 0
        # Set default null values for domain and config instance variables.
        self.tile = None
        self.config = None
        # The class used to construct tile runners.
        self.runner_class = runner_class
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
                print('Initializing tiles...', flush=True)
                if cliargs is None:
                    cliargs = sys.argv
                args = get_arg_handler().parse_args(cliargs[1:])
                config = SCMTilesConfig.from_file(args.config_file_path)
                print('- configuration loaded', flush=True)
                if not os.path.exists(config.output_directory):
                    os.makedirs(config.output_directory)
                    msg = '- created output directory "{}"'
                    print(msg.format(config.output_directory), flush=True)
            except (CLIError, ConfigurationError) as e:
                # An error was detected either in command line arguments or in
                # the parseing of the configuration file. Print the error
                # message and make sure all processes exit with code 0.
                print(str(e), file=sys.stderr, flush=True)
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
                msg = 'Cannot create output directory "{}", permission denied.'
                print(msg.format(config.output_directory), file=sys.stderr,
                      flush=True)
                self.comm.bcast((True, 2), root=TileTask.MASTER)
            else:
                # Broadcast a no error message to all processes.
                self.comm.bcast((False, None), root=TileTask.MASTER)
            num_processes = self.comm.Get_size()
            gm = GridManager(config.xsize, config.ysize, num_processes)
            if self.decompose_mode == 'cells':
                tiles = gm.decompose_by_cells()
            else:
                tiles = gm.decompose_by_rows()
            print('- domain tiled for {} processes'.format(num_processes),
                  flush=True)
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
            print('- initialization complete', flush=True)

    def run(self):
        """Run each task."""
        # Create a tile runner and run all the jobs for the tile.
        if self.is_master:
            print('Running tiles...', flush=True)
        try:
            if self.tile is not None:
                runner = self.runner_class(self.config, self.tile)
        except TileInitializationError as e:
            msg = 'ERROR: tile #{:03d} failed to initialize: {!s}'
            print(msg.format(self.tile.id, e), file=sys.stderr, flush=True)
            run_info = None
        else:
            if self.tile is not None:
                try:
                    run_info = runner.run()
                except TileRunError as e:
                    msg = 'ERROR: tile #{:03d} failed to run: {!s}'
                    print(msg.format(self.tile.id, e), file=sys.stderr,
                          flush=True)
                    run_info = None
            else:
                run_info = None
        # Use an MPI gather call to wait for each process to finish.
        self.run_info = self.comm.gather(run_info, root=TileTask.MASTER)
        if self.is_master:
            print('- running tiles complete', flush=True)

    def finalize(self):
        if not self.is_master:
            # Only the master needs to finalize.
            return 0
        print('Finalizing run...', flush=True)
        # Inspect run_info to determine if any of the tiles failed.
        status = 0
        for tile_result in self.run_info:
            if tile_result is None:
                # Tiles that failed to run have no information.
                continue
            if any([cr.outputs is None for cr in tile_result.cell_results]):
                print('- tile #{:03d} had failed cells:'.format(
                          tile_result.id),
                      file=sys.stderr)
                for cell_result in tile_result.cell_results:
                    if cell_result.outputs is None:
                        status += 1
                        print('  - failed cell: {!s}'.format(cell_result.cell),
                              file=sys.stderr)
                sys.stderr.flush()
        print('- finalization complete')
        return status

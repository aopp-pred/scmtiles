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
from .exceptions import CLIError, CLIHelp, ConfigurationError
from .grid_manager import decompose_domain


class TileTask(object):
    """A single task."""

    #: Rank of the master task, always 0.
    MASTER = 0

    def __init__(self, runner_class):
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

    def initialize(self):
        """
        Initialize the task, setting the domain and configuration.

        """
        if self.is_master:
            # Master task handles command line arguments and distributes
            # the configuration to all workers, as well as assigning a domain
            # for each worker.
            try:
                print('Initializing tiles...', flush=True)
                args = get_arg_handler().parse_args(sys.argv[1:])
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
            tiles = decompose_domain(config.gridx, config.gridy,
                                     num_processes)
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
        # do work in here (all tasks)
        # ...
        # Use an MPI gather call to wait for each process to finish.
        print("[{}]: {!s}".format(self.rank, self.domain))
        process_complete = self.rank
        self.run_info = self.comm.gather(process_complete,
                                         root=SCMTileTask.MASTER)

    def finalize(self):
        if not self.is_master:
            return None
        print('master is finalizing')
        print(self.run_info)
        # Do stuff here for the master task only:
        # ...
        # * Check that each process completed the required number of SCM runs
        #   successfully
        # * identify the files required and concatenate with xarray

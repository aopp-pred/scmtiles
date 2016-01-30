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
import sys
import time

from mpi4py import MPI

from .cli import get_arg_handler
from .config import read_config
from .exceptions import CLIError, CLIHelp, ConfigurationError
from .grid_manager import decompose_domain


class SCMTileTask(object):
    """A single task."""

    #: Rank of the master task, always 0.
    MASTER = 0

    def __init__(self):
        """Create an SCM Tiles task."""
        # Define an MPI communicator.
        self.comm = MPI.COMM_WORLD
        # Determine if this task is the master task.
        self.rank = self.comm.Get_rank()
        self.is_master = self.rank == 0
        # Set default null values for domain and config instance variables.
        self.domain = None
        self.config = None

    def initialize(self):
        """
        Initialize the task, setting the domain and configuration.
        
        """
        # Might need a separate initializer to handle arguments to prevent
        # other trheads from stalling... need to do something anyway.
        if self.is_master:
            # Master task handles command line arguments and distributes
            # the configuration to all workers, as well as assigning a domain
            # for each worker.
            try:
                arg_handler = get_arg_handler(sys.argv[1:])
                config = read_config(arg_handler.config_file_path)
                # TODO: Validate config here? Examples include checking paths
                #       are readable/writable and if grid sizes are positive.
            except (CLIError, ConfigurationError) as e:
                # An error was detected in command line arguments, print the
                # error message and make sure all processes exit with exit
                # code 0.
                print(str(e), file=sys.stderr)
                sys.stderr.flush()
                self.comm.bcast((True, 1), root=SCMTileTask.MASTER)
                exit(1)
            except CLIHelp as e:
                # CLIHelp is raised when the program was run with the help
                # option, which should exit once the help is printed to the
                # screen using code 0.
                self.comm.bcast((True, 0), root=SCMTileTask.MASTER)
                exit(0)
            else:
                self.comm.bcast((False, None), root=SCMTileTask.MASTER)
                print('no error, continue')
            domains = decompose_domain(config.gridx, config.gridy,
                                       self.comm.Get_size())
        else:
            # Receive an error package from the master process, if an error
            # condition has been encountered by the master process then exit
            # with the provided exit code.
            error, stat = self.comm.bcast(None, root=SCMTileTask.MASTER)
            if error:
                exit(stat)
            # Worker tasks will be given the appropriate configuration and
            # domain objects.
            domains = None
            config = None
        # Use an MPI broadcast to send the configuration object to all tasks. 
        self.config = self.comm.bcast(config, root=SCMTileTask.MASTER)
        # Use an MPI scatter to send one domain to each task.
        self.domain = self.comm.scatter(domains, root=SCMTileTask.MASTER)

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

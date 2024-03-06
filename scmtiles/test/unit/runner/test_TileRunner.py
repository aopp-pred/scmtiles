"""Test for `scmtiles.runner.TileRunner`."""
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

import unittest
from unittest.mock import MagicMock, patch

from scmtiles.runner import TileRunner
from scmtiles.exceptions import TileRunError


class ConcreteTileRunner(TileRunner):
    """A concrete class derived from the abstract TileRunner class."""

    def run_cell(self, cell, logger):
        pass


class Test_create_run_directory(unittest.TestCase):

    def test_permission_error(self):
        config = MagicMock(name='SCMTilesConfig')
        tile = MagicMock(name='Tile')
        # Don't have permission to write to the root directory.
        config.work_directory = '/'
        error_message = 'Cannot create run directory in "/".'
        # Patch _load_tile_data so it doesn't do anything.
        with patch.object(ConcreteTileRunner, '_load_tile_data') as mock_ltd:
            mock_ltd.return_value = None
            r = ConcreteTileRunner(config, tile)
            with self.assertRaisesRegex(TileRunError, error_message):
                r.create_run_directory()

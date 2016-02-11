"""Tests for the `scmtiles.grid_manager.LinearTile` class."""
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

from scmtiles.grid_manager import LinearTile


class Test(unittest.TestCase):

    def test_cells(self):
        selector = slice(2, 7)
        x_indices = [0, 1, 2, 0, 1, 2, 0, 1, 2][selector]
        y_indices = [0, 0, 0, 1, 1, 1, 2, 2, 2][selector]
        tile = LinearTile(1, selector, x_indices, y_indices)
        expected_x = [0, 1, 2, 3, 4]
        for i, cell in enumerate(tile.cells()):
            self.assertEqual(cell.x, expected_x[i])
            self.assertEqual(cell.x_global, x_indices[i])
            self.assertEqual(cell.y_global, y_indices[i])

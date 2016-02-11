"""Tests for the `scmtiles.grid_manager.RectangularTile` class."""
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

from scmtiles.grid_manager import RectangularTile


class Test(unittest.TestCase):

    def test_cells(self):
        xselector = slice(1, 3)
        yselector = slice(1, 3)
        x_indices = [1, 2]
        y_indices = [1, 2]
        tile = RectangularTile(1, xselector, yselector, x_indices, y_indices)
        expected_x = [0, 1, 0, 1]
        expected_y = [0, 0, 1, 1]
        expected_x_global = [1, 2, 1, 2]
        expected_y_global = [1, 1, 2, 2]
        for i, cell in enumerate(tile.cells()):
            self.assertEqual(cell.x, expected_x[i])
            self.assertEqual(cell.y, expected_y[i])
            self.assertEqual(cell.x_global, expected_x_global[i])
            self.assertEqual(cell.y_global, expected_y_global[i])

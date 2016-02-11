"""Tests for the `scmtiles.grid_manager.Cell` class."""
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

from scmtiles.grid_manager import Cell


class Test(unittest.TestCase):

    def test_rectangular(self):
        cell = Cell(9, 10, 4, 5)
        self.assertEqual(cell.x, 4)
        self.assertEqual(cell.y, 5)

    def test_linear(self):
        cell = Cell(12, 13, 101)
        self.assertEqual(cell.x, 101)
        expected_error = "Cell has no attribute 'y'"
        with self.assertRaisesRegex(AttributeError, expected_error):
            y = cell.y

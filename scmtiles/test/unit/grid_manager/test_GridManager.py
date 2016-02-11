"""Tests for the `scmtiles.grid_manager.GridManager` class."""
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

from scmtiles.grid_manager import GridManager


class Test_decompose_by_rows(unittest.TestCase):

    def _check_tile_coverage(self, tiles, nx, ny):
        xs = [tile.xselector for tile in tiles]
        for xsel in xs:
            self.assertEqual(xsel.start, 0)
            self.assertEqual(xsel.stop, nx)
        ys = [tile.yselector for tile in tiles]
        last_stop = 0
        for ysel in ys:
            self.assertEqual(ysel.start, last_stop)
            last_stop = ysel.stop
        self.assertEqual(ys[-1].stop, ny)

    def test_equal(self):
        nx = 4
        ny = 5
        workers = 5
        gm = GridManager(nx, ny, workers)
        tiles = gm.decompose_by_rows()
        self.assertEqual(len(tiles), workers)
        self.assertFalse(_is_degenerate(tiles))
        self._check_tile_coverage(tiles, nx, ny)

    def test_unequal(self):
        nx = 4
        ny = 5
        workers = 4
        gm = GridManager(nx, ny, workers)
        tiles = gm.decompose_by_rows()
        self.assertEqual(len(tiles), workers)
        self.assertFalse(_is_degenerate(tiles))
        self._check_tile_coverage(tiles, nx, ny)

    def test_degenerate(self):
        nx = 4
        ny = 5
        workers = 6
        gm = GridManager(nx, ny, workers)
        tiles = gm.decompose_by_rows()
        self.assertEqual(len(tiles), workers)
        self.assertTrue(_is_degenerate(tiles))
        non_degenerate_tiles = [tile for tile in tiles if tile is not None]
        self.assertEqual(len(non_degenerate_tiles), ny)
        self._check_tile_coverage(non_degenerate_tiles, nx, ny)


class Test_decompose_by_cells(unittest.TestCase):

    def _check_tile_coverage(self, tiles, ng):
        s = [tile.selector for tile in tiles]
        last_stop = 0
        for sel in s:
            self.assertEqual(sel.start, last_stop)
            last_stop = sel.stop
        self.assertEqual(s[-1].stop, ng)

    def test_standard(self):
        nx = 4
        ny = 5
        workers = 8
        gm = GridManager(nx, ny, workers)
        tiles = gm.decompose_by_cells()
        self.assertEqual(len(tiles), workers)
        self.assertFalse(_is_degenerate(tiles))
        self._check_tile_coverage(tiles, nx * ny)

    def test_degenerate(self):
        nx = 4
        ny = 5
        workers = 21
        gm = GridManager(nx, ny, workers)
        tiles = gm.decompose_by_cells()
        self.assertEqual(len(tiles), workers)
        self.assertTrue(_is_degenerate(tiles))
        non_degenerate_tiles = [tile for tile in tiles if tile is not None]
        self.assertEqual(len(non_degenerate_tiles), nx * ny)
        self._check_tile_coverage(non_degenerate_tiles, nx * ny)


def _is_degenerate(tiles):
    return any(tile is None for tile in tiles)

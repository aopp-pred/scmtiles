"""Grid decomposition and management."""
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
from itertools import accumulate


class Cell(object):
    """A single grid cell."""

    def __init__(self, x_global, y_global, x, y=None):
        #: The x-direction index of the cell in the full grid.
        self.x_global = x_global
        #: The y-direction index of the cell in the full grid.
        self.y_global = y_global
        #: The x-direction index of the cell within its tile.
        self.x = x
        self._y = y

    @property
    def y(self):
        """The y-direction index of the cell within its tile."""
        if self._y is None:
            raise AtrributeError("Cell has not attribute 'y'.")
        return self._y

    def __repr__(self):
        if self._y is None:
            r = 'Cell(x_global={c.x_global}, y_global={c.y_global}, x={c.x})'
        else:
            r = ('Cell(x_global={c.x_global}, y_global={c.y_global} '
                 'x={c.x}, y={c.y})')
        return r.format(c=self)


class Tile(metaclass=ABCMeta):

    def __init__(self, tile_id, tile_type):
        self.id = tile_id
        self.type = tile_type

    @abstractmethod
    def cells(self):
        """
        Generator of cell information, yielding `Cell` instances for
        each cell in the tile. Must be defined on subclasses.

        """
        pass


class LinearTile(Tile):

    def __init__(self, tile_id, selector, x_indices, y_indices):
        """
        Create a `LinearTile` instance.

        **Arguments:**

        * tile_id
            Unique identifier for the tile.

        * selector
            A selector that when applied to the linear grid will return
            the area covered by this tile.

        * x_indices
            The linear grid indices for the x-direction.

        * y_indices
            The linear grid indices for the y-direction.

        """
        super().__init__(tile_id, 'linear')
        self.selector = selector
        self._xi = x_indices
        self._yi = y_indices

    def cells(self):
        """
        Generator of cell information, yielding `Cell` instances for
        each cell in the tile.

        """
        for e, (xi, yi) in enumerate(zip(self._xi, self._yi)):
            yield Cell(xi, yi, e)

    def __str__(self):
        return "ID={} Interval=[{}, {})".format(self.id, self.selector.start,
                                                self.selector.stop)


class RectangularTile(Tile):

    def __init__(self, tile_id, xselector, yselector, x_indices, y_indices):
        """
        Create a `RectangularTile` instance.

        **Arguments:**

        * tile_id
            Unique identifier for the tile.

        * xselector, yselector
            Selectors that when applied to the grid will return the area
            covered by this tile.

        * x_indices
            The grid indices for the x-direction.

        * y_indices
            The grid indices for the y-direction.

        """
        super().__init__(tile_id, 'rectangular')
        self.xselector = xselector
        self.yselector = yselector
        self._xi = x_indices
        self._yi = y_indices

    def cells(self):
        """
        Generator of cell information, yielding `Cell` instances for
        each cell in the tile.

        """
        for y, yi in enumerate(self._yi):
            for x, xi in enumerate(self._xi):
                yield Cell(xi, yi, x, y)

    def __str__(self):
        return "ID={} X-interval=[{}, {}) Y-interval=[{}, {})".format(
            self.id, self.xselector.start, self.xselector.stop,
            self.yselector.start, self.yselector.stop)


class GridManager(object):

    def __init__(self, nx, ny, workers):
        """
        Create a `GridManager` for a given grid.

        **Arguments:**

        * nx, ny
            The dimensions of the grid in the x- and y-directions.

        * workers
            The number of worker processes that will process the grid.

        """
        self.nx = nx
        self.ny = ny
        self.workers = workers

    def decompose_by_rows(self):
        """
        Decompose a grid into a set of tiles, one for each worker. The
        sub-domains are a number of whole rows of the grid.

        **Returns:**

        * tiles
            A list of `RectangularTile` objects, one for each worker. If
            there are more workers than required to tile the domain then
            this method will return a `None` value instead of a
            `RectangularTile` instance for workers who don't have a tile
            to process.

        """
        base = self.ny // self.workers
        num_extra = self.ny % self.workers
        rows_per_worker = [base + 1 if n < num_extra else base
                           for n in range(self.workers)]
        rows_per_worker = [r for r in rows_per_worker if r != 0]
        ends = list(accumulate(rows_per_worker))
        starts = [0] + ends[:-1]
        xi = [x for x in range(self.nx)]
        yi = [y for y in range(self.ny)]
        tiles = [RectangularTile(n, slice(0, self.nx), slice(start, end),
                                 xi, yi[slice(start, end)])
                 for n, (start, end) in enumerate(zip(starts, ends))]
        if len(tiles) < self.workers:
            tiles += [None] * (self.workers - len(tiles))
        return tiles

    def decompose_by_cells(self):
        """
        Decompose a grid into a set of tiles, one for each worker. The
        tiles consist of a number of cells from the grid.

        **Returns:**

        * tiles
            A list of `LinearTile` objects, one for each worker. If
            there are more workers than required to tile the domain then
            this method will return a `None` value instead of a
            `LinearTile` instance for workers who don't have a tile to
            process.

        """
        grid_size = self.nx * self.ny
        base = grid_size // self.workers
        num_extra = grid_size % self.workers
        cells_per_worker = [base + 1 if n < num_extra else base
                            for n in range(self.workers)]
        cells_per_worker = [c for c in cells_per_worker if c != 0]
        ends = list(accumulate(cells_per_worker))
        starts = [0] + ends[:-1]
        xi = [x for _ in range(self.ny) for x in range(self.nx)]
        yi = [y for y in range(self.ny) for _ in range(self.nx)]
        tiles = [LinearTile(n, slice(start, end),
                            xi[slice(start, end)],
                            yi[slice(start, end)])
                 for n, (start, end) in enumerate(zip(starts, ends))]
        if len(tiles) < self.workers:
            tiles += [None] * (self.workers - len(tiles))
        return tiles

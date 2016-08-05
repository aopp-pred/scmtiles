# SCM Tiles

Toolkit for running a single-column model over a grid.


## Usage

scmtiles is a framework for running an arbitrary single-column model over
a grid. It provides high-level task organisation and paralellisation for
managing many thousands (or more) of model runs.

In order to use scmtiles you must write your own runner class, a subclass of
`scmtiles.runner.TileRunner` that implements the `run_cell()` method. The
`run_cell()` method contains all the specific logic and operations required to
run a particular SCM at a single location in space.


## Installation

scmtiles reuires Python 3.5 or higher and
[setuptools](https://setuptools.readthedocs.io/en/latest/) for installation
The following dependencies are required to run scmtiles:

* [mpi4py](http://mpi4py.readthedocs.io/)
* [dateutil](https://dateutil.readthedocs.io/)
* [xarray](http://xarray.pydata.org/en/v0.7.1/) < 0.8.0
* [netcdf4](http://unidata.github.io/netcdf4-python/)
* [dask](http://dask.pydata.org/) >= 0.8.1
* [versioneer](https://github.com/warner/python-versioneer)

Once you have the dependencies installed you can install scmtiles with:

    python setup.py install

If you want to run the test suite you need the following extra packages
installed:

* [pytest](http://doc.pytest.org/)
* [pep8](https://pypi.python.org/pypi/pep8)


## Contributing

Contributions small or large are welcomed. If you find a bug or would like to
see a new feature, please open a ticket on the
[Github issue tracker](https://github.com/aopp-pred/scmtiles/issues).

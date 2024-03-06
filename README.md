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

For an example of use see the project
[openifs-scmtiles](https://github.com/aopp-pred/openifs-scmtiles) which
implements a tile runner for the OpenIFS SCM.


## Installation

scmtiles reuires Python 3.8 or higher. The following dependencies are
required to run scmtiles:

* [mpi4py](http://mpi4py.readthedocs.io/)
* [dateutil](https://dateutil.readthedocs.io/)
* [xarray](http://xarray.pydata.org/en/v0.7.1/)
* [netcdf4](http://unidata.github.io/netcdf4-python/)
* [dask](http://dask.pydata.org/)

You can install scmtiles (likely within a virtualenv or conda env) with:

    python -m pip install .

This will install scmtiles and any required dependencies. If you want to
run the test suite you need the following extra packages installed:

* [pytest](http://doc.pytest.org/)
* [pycodestyle](https://pycodestyle.pycqa.org/en/latest/)

### Bootstrapping

For a no-hassle installation of scmtiles plus all dependencies (including
Python itself) you can use the bundled `bootstrap_scmtiles.sh` script. This
script requires bash to run, and will (optionally) download and install
[miniconda](http://conda.pydata.org/miniconda.html), create a conda environment
for scmtiles with all dependencies installed, and then install scmtiles into
the environment. Basic usage is:

    curl -o bootstrap_scmtiles.sh https://raw.githubusercontent.com/aopp-pred/scmtiles/master/bootstrap_scmtiles.sh
    bash bootstrap_scmtiles.sh my_project_name

which will install miniconda to `my_project_name/miniconda3` and create an
environment with name `scmtiles`. You can change the name of the environment
and even specify an existing miniconda installation to use instead of making
a new one. You can also set the revision of scmtiles you'd like to install,
which can be any valid git version identifier (e.g., commit hash, tag, branch
name). For help use:

    bash bootstrap_scmtiles.sh -h

## Contributing

Contributions small or large are welcomed. If you find a bug or would like to
see a new feature, please open a ticket on the
[Github issue tracker](https://github.com/aopp-pred/scmtiles/issues).

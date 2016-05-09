#!/usr/bin/env python
"""Prepare an scmtiles execution environment."""
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
from __future__ import absolute_import, division, print_function

from optparse import OptionParser
import os
import stat
from subprocess import check_call, CalledProcessError
try:
    from subprocess import check_output
except ImportError:
    from subprocess import Popen, PIPE

    def check_output(cmd):
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p.communicate()
        if p.returncode != 0:
            raise CalledProcessError('failed to run the command: '
                                     '{0!s}'.format(cmd))
        try:
            p.kill()
        except OSError:
            pass
        return stdout

import sys
if sys.version_info[0] == 2:
    from urllib2 import URLError, urlopen
    from urlparse import urlsplit
else:
    from urllib.error import URLError
    from urllib.parse import urlsplit
    from urllib.request import urlopen


class Error(Exception):
    """Exception class for generic errors."""
    pass


if sys.version_info[0] == 2:

    class PermissionError(Exception):
        pass


def get_header(header_name, response):
    """
    Get a header from an HTTP response from urlopen().

    This is a Python version independent wrapper for obtaining an HTTP
    header.

    **Arguments:**

    * header-name:
        The name of the HTTP header.

    * response:
        The response from calling urlopen().

    """
    if sys.version_info[0] == 2:
        header = response.info().getheaders(header_name)[0]
    else:
        header = response.getheader(header_name)
    return header


def download_file(url, target_path=None, block_size=8192, progress=False):
    """
    Download a file from a URL.

    **Argument:**

    * url:
        The URL of the file to download.

    **Keyword arguments:**

    * target_path:
        The local path of the resulting downloaded file. If not given
        the downloaded file will be in the current directory with the
        same name it has on the server.

    * block_size:
        The file will be downloaded in blocks of the given size. The
        default size is 8192 bytes.

    * progress:
        If `True` a progress indicator will be displayed on stdout
        during the download. The default is `False` (no indicator).

    **Returns:**

    * dowloaded_path:
        The path to the downloaded file. If `target_path` was specified
        then this will just be `target_path`.

    """
    if target_path is None:
        target_path = os.path.basename(urlsplit(url).path)
    try:
        fremote = urlopen(url)
    except URLError as e:
        # TODO: raise different errors here for no connection and for
        #       URL not located (and indeed for anything else).
        raise Error('Cannot locate file: {0!s}'.format(url))
    try:
        with open(target_path, 'wb') as flocal:
            if progress:
                downloaded_size = 0
                total_size = int(get_header('Content-Length', fremote))
                sys.stdout.write('Downloading: {0!s} ['.format(target_path))
            while True:
                buffer = fremote.read(block_size)
                if not buffer:
                    break
                flocal.write(buffer)
                if progress:
                    downloaded_size += len(buffer)
                    percent_complete = 100 * downloaded_size / total_size
                    status = '{0:5.1f} %]'.format(percent_complete)
                    sys.stdout.write(status)
                    sys.stdout.write('\b' * len(status))
                    sys.stdout.flush()
            if progress:
                sys.stdout.write('\n')
    except OSError:
        msg = 'Failed to download {0!s} to {1!s}'
        raise Error(msg.format(url, target_path))
    return target_path


def download_miniconda(download_dir=None):
    """
    Download the appropriate Miniconda3 installer for the current
    operating system from Continuum Analytics.

    **Keyword argument:**

    * download_dir:
        The directory to download the installer into. Default is the
        current working directory.

    **Returns:**

    * downloaded_path:
        The path to the downloaded installer.

    """
    miniconda_base_url = 'https://repo.continuum.io/miniconda/'
    os_name = os.uname()[0].lower()
    if os_name == 'linux':
        miniconda_installer = 'Miniconda3-latest-Linux-x86_64.sh'
    elif os_name == 'darwin':
        miniconda_installer = 'Miniconda3-latest-MacOSX-x86_64.sh'
    else:
        raise Error('Cannot install on OS: {0!s}'.format(os_name))
    miniconda_url = os.path.join(miniconda_base_url, miniconda_installer)
    if download_dir is not None:
        target_path = os.path.join(download_dir, miniconda_installer)
    else:
        target_path = miniconda_installer
    download_file(miniconda_url, target_path, progress=True)
    return target_path


def install_miniconda(miniconda_installer, miniconda_install_dir):
    """
    Run the Miniconda installer.

    **Arguments:**

    * miniconda_installer
        The path to the Miniconda installer.

    * miniconda_install_dir
        The path where Miniconda should be installed.

    **Returns:**

    * miniconda_install_path
        The path to the installed Miniconda (this is the same as
        `miniconda_install_dir`).

    """
    command = ['bash', miniconda_installer, '-b', '-p', miniconda_install_dir]
    try:
        check_call(command)
    except CalledProcessError:
        msg = 'Failed to install miniconda in: {0!s}'
        raise Error(msg.format(miniconda_install_dir))
    return os.path.join(miniconda_install_dir, 'bin')


def create_directory(path):
    """Create a directory, raising an exception if not possible."""
    try:
        os.makedirs(path)
    except (OSError, PermissionError):
        msg = ('Cannot create an scmtiles project in "{0:s}", '
               'permission denied')
        raise Error(msg.format(path))


def clone_repository(repo_url, target):
    """
    Clone a git repository to a given location.

    """
    command = ['git', 'clone', repo_url, target]
    try:
        check_call(command)
    except CalledProcessError:
        msg = ('Failed to clone repository "{0:s}", check the URL is correct '
               'and that you have the necessary access permissions')
        raise Error(msg.format(repo_url))
    except FilenotFoundError:
        raise Error('Failed to clone repository, is git installed?')
    return target


def checkout_revision(repo_dir, revision_id):
    checkout_command = ['git', 'checkout', revision_id]
    try:
        check_call(checkout_command, cwd=repo_dir)
    except CalledProcessError:
        msg = ('Failed to checkout revision "{0:s}", check that the '
               'commit/branch/tag exists')
        raise Error(msg.format(revision_id))
    return revision_id


def clone_scmtiles(scmtiles_dir):
    """
    Clone the scmtiles git repository to a specified location.

    """
    scmtiles_url = 'git@gitlab.physics.ox.ac.uk:dawson/scmtiles.git'
    return clone_repository(scmtiles_url, scmtiles_dir)


def install_python_package(package_directory, python=None):
    """
    Install a Python package.

    """
    if python is None:
        python = 'python'
    command = [python, 'setup.py', 'install']
    try:
        check_call(command, cwd=package_directory)
    except CalledProcessError:
        msg = ('Failed to install Python package from "{0:s}", '
               'check permissions')
        raise Error(msg.format(package_directory))
    except FileNotFoundError as e:
        if package_directory in str(e):
            msg = ('Cannot install Python package from "{lib:s}", the source '
                   'directory does not exist or cannot be accessed')
        else:
            msg = ('Failed to install Python package from "{lib:s}, does '
                   '{python:s} exist and is it executable?')
        raise Error(msg.format(lib=package_directory, python=python))


def install_scmtiles(env_path, scmtiles_path):
    """
    Install the scmtiles Python package.

    """
    env_python = os.path.abspath(os.path.join(env_path, 'bin', 'python'))
    install_python_package(scmtiles_path, python=env_python)


def create_environment(miniconda_path, scmtiles_path, env_name):
    """
    Create a conda environment compatible with scmtiles.

    Expects to find a requirements file within the scmtiles source
    directory named "conda-requirements.txt".

    **Arguments:**

    * miniconda_path
        The path to the root of the miniconda installation.

    * scmtiles_path
        The path to the scmtiles source directory.

    * env_name
        The name of the environment to create.

    **Returns:**

    * env_path
        The path to the created environment.

    """
    conda = os.path.abspath(os.path.join(miniconda_path, 'bin', 'conda'))
    requirements = os.path.join(scmtiles_path, 'conda-requirements.txt')
    create_command = [conda, 'create', '-n', env_name, '--quiet', '--yes',
                      '--file', requirements]
    try:
        check_call(create_command)
    except CalledProcessError:
        msg = 'Failed to create an environment from {0:s}, does it exist?'
        raise Error(msg.format(requirements))
    except FileNotFoundError:
        msg = ('Failed to create a conda environment, does {0:s} exist '
               'and is it executable?')
        raise Error(msg.formst(conda))
    locate_command = [conda, 'env', 'list']
    try:
        response = check_output(locate_command)
    except (FileNotFoundError, CalledProcessError):
        msg = ('Failed to create a conda environment, does {0:s} exist '
               'and is it executable?')
        raise Error(msg.formst(conda))
    env_mapping = dict(
        [(env.split()[0], env.split()[1])
         for env in response.decode('utf-8').replace('*', '').split('\n')
         if env and not env.startswith('#')])
    return env_mapping[env_name]


def create_support_script(template, target, base_path, miniconda_path,
                          env_name, scmtiles_path):
    """
    Create a support shell script.

    **Arguments:**

    * template
        A string to be interpolated to produce the shell script. The
        following variables are provided to the interpolation:

    * target
        The path to the resulting shell script.

    * base_path
        The path to the base project directory.

    * miniconda_path
        The path to the root of the miniconda installation.

    * env_name
        The name of the conda environment used by the project.

    * scmtiles_path
        The path to the scmtiles source directory.

    """
    miniconda_bin_path = os.path.join(os.path.abspath(miniconda_path), 'bin')
    script = template.format(
        miniconda_bin_path=miniconda_bin_path,
        scmtiles_env_name=env_name,
        scmtiles_path=os.path.abspath(scmtiles_path))
    try:
        with open(target, 'w') as fh:
            fh.write(script)
        st = os.stat(target)
        os.chmod(target, st.st_mode | stat.S_IXUSR)
    except IOError:
        raise Error('Failed to write script: {0!s}'.format(target))


def create_support_scripts(base_path, miniconda_path, env_name,
                           scmtiles_path):
    """
    Create bash scripts to update the scmtiles installation and to
    interact with the conda environment for this project.

    **Arguments:**

    * base_path
        The path to the base project directory.

    * miniconda_path
        The path to the root of the miniconda installation.

    * env_name
        The name of the conda environment used by the project.

    * scmtiles_path
        The path to the scmtiles source directory.

    """
    update_scmtiles_path = os.path.join(base_path, 'update_scmtiles.sh')
    scmenv_path = os.path.join(base_path, 'scmenv.sh')
    create_support_script(_UPDATE_SCMTILES_TEMPLATE, update_scmtiles_path,
                          base_path, miniconda_path, env_name, scmtiles_path)
    create_support_script(_SCMENV_TEMPLATE, scmenv_path,
                          base_path, miniconda_path, env_name, scmtiles_path)


def main(argv=None):
    if argv is None:
        # Use command line arguments if none are passed.
        argv = sys.argv
    # Set-up an argument parser and parse all arguments:
    ap = OptionParser()
    ap.add_option(
        '-m', '--miniconda-path', type=str,
        help='root of an existing Miniconda install to be used')
    ap.add_option(
        '-e', '--env-name', type=str,
        help='name for the environment within Miniconda, useful with -m')
    ap.add_option(
        '-r', '--revision', type=str,
        help=('a git revision (commit/branch/tag) to checkout from '
              'the scmtiles repository'))
    opts, args = ap.parse_args(argv[1:])
    try:
        if len(args) != 1:
            raise Error('expected one argument, the name of the '
                        'base directory')
        # Take an absolute reference to the specified base directory, ensuring
        # all paths are absolute:
        base_directory = os.path.abspath(args[0])
        # Create the base directory if it doesn't already exist:
        if not os.path.exists(base_directory):
            print('Creating base directory "{0:s}"'.format(base_directory))
            create_directory(base_directory)
        # If an scmtiles source directory already exists then we raise an
        # error, as we have no way of knowing what is in it.
        scmtiles_path = os.path.join(base_directory, 'scmtiles')
        if os.path.exists(scmtiles_path):
            msg = ('The directory "{0!s}" already contains scmtiles source '
                   'code, please choose an empty directory.')
            raise Error(msg.format(base_directory))
        # Install Miniconda3 if required, the user can specify to use an
        # existing Miniconda install.:
        if opts.miniconda_path is None:
            miniconda_path = os.path.join(base_directory, 'miniconda3')
            if os.path.exists(miniconda_path):
                msg = ('The directory "{0!s}" already contains a Mininconda '
                       'installation, please choose an empty directory.')
                raise Error(msg.format(base_directory))
            installer_path = download_miniconda(base_directory)
            install_miniconda(installer_path, miniconda_path)
            os.remove(installer_path)
        else:
            miniconda_path = opts.miniconda_path
        # Install scmtiles:
        clone_scmtiles(scmtiles_path)
        if opts.revision is not None:
            checkout_revision(scmtiles_path, opts.revision)
        env_name = opts.env_name or 'scmtiles'
        env_path = create_environment(miniconda_path, scmtiles_path, env_name)
        install_scmtiles(env_path, scmtiles_path)
        # Create support scripts in the base directory:
        create_support_scripts(base_directory, miniconda_path, env_name,
                               scmtiles_path)
    except Error as e:
        print('error: {0!s}'.format(e), file=sys.stderr)
        return 2


#: Template for update_scmtiles.sh support script.
_UPDATE_SCMTILES_TEMPLATE = """#!/bin/bash
#
# Auto-update the scmtiles version used in this project.
#
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

error () {{
    echo "error: $@" 1>&2
}}

main () {{
    # Activate the required conda environment:
    export PATH="{miniconda_bin_path:s}:$PATH"
    source activate {scmtiles_env_name:s}
    if [[ $? -ne 0 ]]; then
        error "cannot activate the scmtiles conda environment"
        exit 1
    fi
    # Enter the scmtiles git repository directory:
    cd "{scmtiles_path:s}"
    if [[ $? -ne 0 ]]; then
        error "cannot find scmtiles source in {scmtiles_path:s}"
        return 2
    fi
    # Fetch the latest changes:
    git pull
    if [[ $? -ne 0 ]]; then
        error "cannot update source, check repository status and connection"
        return 3
    fi
    # Install the updated scmtiles version:
    python setup.py install
    if [[ $? -ne 0 ]]; then
        error "failed to update the scmtiles installation"
        return 4
    fi
}}

main $@
exit $?
"""

#: Template for scmenv.sh support script.
_SCMENV_TEMPLATE = """#!/bin/bash
#
# Interact with the scmtiles Python environment.
#
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

error () {{
    echo "error: $@" 1>&2
}}

main () {{
    # Activate the required conda environment:
    export PATH="{miniconda_bin_path:s}:$PATH"
    source activate {scmtiles_env_name:s} 2> /dev/null
    if [[ $? -ne 0 ]]; then
        error "cannot activate the scmtiles conda environment"
        exit 1
    fi
    PS1="scmtiles-env> " bash --norc --noprofile
    return 0
}}

main $@
exit $?
"""


if __name__ == '__main__':
    sys.exit(main())

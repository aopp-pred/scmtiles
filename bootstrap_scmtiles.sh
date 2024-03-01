#!/bin/bash
#
# Prepare an scmtiles execution environment
#
set -e -o pipefail

# ----------------------------------------------------------------------------
# Program constants
# ----------------------------------------------------------------------------

readonly MINICONDA_URL="https://repo.anaconda.com/miniconda"
readonly SCMTILES_REPO="https://github.com/aopp-pred/scmtiles.git"

readonly PROG=$( basename "$0" )
readonly USAGE="usage: $PROG [<options>] <install_dir>

    -c,       Use an existing conda from PATH, default is to install our own
    -e ENV    The conda environment name to use, default is scmtiles
    -r REV    Specify a revision of scmtiles to use instead of the git default
"


# ----------------------------------------------------------------------------
# Handle command line options and arguments
# ----------------------------------------------------------------------------

args=$( getopt hce:r: $* )
if [[ $? -ne 0 ]]; then
    echo "$USAGE" 1>&2
    exit 1
fi
eval set -- "$args"

INSTALL_CONDA=true
ENV_NAME="scmtiles"
REVISION=""
while true; do
    case "$1" in
        -c | --conda)
            INSTALL_CONDA=false
            shift
            ;;
        -e | --env-name)
            ENV_NAME="$2"
            shift
            shift
            ;;
        -r | --revision)
            REVISION="$2"
            shift
            shift
            ;;
        -h | --help)
            echo "$USAGE"
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "$USAGE" 1>&2
            exit 1
            ;;
    esac
done
readonly INSTALL_CONDA
readonly ENV_NAME
readonly REVISION

if [[ $# -ne 1 ]]; then
    echo "error: you need to specify an installtion directory" 1>&2
    exit 1
fi
mkdir -p "$1" || {
    echo "error: cannot create root directory" 1>&2
    exit 1
}
ROOT_DIR=$( realpath "$1" )

# Check if scmtiles already in root, if so abort
if [[ -d "$ROOT_DIR/scmtiles" ]]; then
    echo "error: the root directory already contains an scmtiles directory" 1>&2
    exit 1
fi

# ----------------------------------------------------------------------------
# Install conda if we need it
# ----------------------------------------------------------------------------

if $INSTALL_CONDA; then
    # Abort if there is already a miniconda3 directory
    if [[ -d "$ROOT_DIR/miniconda3" ]]; then
        echo "error: the root directory already contains a miniconda3 directory" 1>&2
        exit 1
    fi

    # Download a miniconda installer
    system=$( uname -s )
    if [[ "$system" == "Darwin" ]]; then
        system="MacOSX"
    fi
    machine=$( uname -m )
    curl -o "$ROOT_DIR/miniconda_installer.sh" "$MINICONDA_URL/Miniconda3-latest-${system}-${machine}.sh"
    chmod u+x "$ROOT_DIR/miniconda_installer.sh"

    # Run the installer in batch mode using the given root as prefix
    "$ROOT_DIR/miniconda_installer.sh" -b -p "$ROOT_DIR/miniconda3"

    # Set up this shell to use conda
    export PATH="$ROOT_DIR/miniconda3/bin:$PATH"

    # Clean up
    rm -f "$ROOT_DIR/miniconda_installer.sh"
fi


# ----------------------------------------------------------------------------
# Set up a conda env with scmtiles installed
# ----------------------------------------------------------------------------

# Checkout and install scmtiles
git -C "$ROOT_DIR" clone "$SCMTILES_REPO" scmtiles

# Switch to the specified revision, if one was requested
if [[ -n "$REVISION" ]]; then
    git -C "$ROOT_DIR/scmtiles" checkout "$REVISION"
fi

# Create the conda environment to install scmtiles into
conda create -c conda-forge -n "$ENV_NAME" --quiet --yes --file "$ROOT_DIR/scmtiles/conda-requirements.txt"
eval "$( conda shell.bash activate "$ENV_NAME" )"

# Install the scmtile package into the environment
python -m pip install "$ROOT_DIR/scmtiles"


# ----------------------------------------------------------------------------
# Create helper scripts
# ----------------------------------------------------------------------------

# Keep the conda executable fixed at the one we are using right now.
CONDA=$( which conda )

# Create a script to activate the environment
cat > "$ROOT_DIR/scmenv.sh" << EOF
#!/bin/bash
set -e

conda_setup=\$( "$CONDA" shell.bash activate "$ENV_NAME" || true )
if [[ -z "\$conda_setup" ]]; then
    echo "error: cannot activate env '$ENV_NAME'"
    exit 1
fi
eval "\$conda_setup"

PS1="scmtiles-env> " bash --norc --noprofile
EOF

# Create a script to update the scmtiles source and reinstall in the conda env
cat > "$ROOT_DIR/update_scmtiles.sh" << EOF
#!/bin/bash
set -e

conda_setup=\$( "$CONDA" shell.bash activate "$ENV_NAME" || true )
if [[ -z "\$conda_setup" ]]; then
    echo "error: cannot activate env '$ENV_NAME'"
    exit 1
fi
eval "\$conda_setup"

cd "$ROOT_DIR/scmtiles" || {
    echo "error: cannot find scmtiles source in '$ROOT_DIR/scmtiles'" 1>&2
    exit 1
}

git pull || {
    echo "error: cannot update source, check repository status and connection" 1>&2
    exit 1
}

python -m pip install . || {
    echo "error: failed to update the scmtiles installation" 1>&2
    exit 1
}
EOF

# Make these helper scripts executable
chmod u+x "$ROOT_DIR/scmenv.sh" "$ROOT_DIR/update_scmtiles.sh"

#!/bin/bash

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$ROOT_DIR/venv"
PYTHON_SCRIPT="$ROOT_DIR/src/Working_Code.py"

# Function to setup venv
setup_venv() {
    echo "Initializing Time Tracker Environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip --quiet
    "$VENV_DIR/bin/pip" install rich typer --quiet
    echo "Environment Ready."
}

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    setup_venv
fi

# Execute script with arguments
# We use exec to replace the shell process with the python process
exec "$VENV_DIR/bin/python" "$PYTHON_SCRIPT" "$@"

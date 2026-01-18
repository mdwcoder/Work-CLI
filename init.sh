#!/bin/bash

# Get the absolute path of the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_PATH="$SCRIPT_DIR/working_runner.sh"

# Ensure the runner is executable
chmod +x "$RUNNER_PATH"

echo "╔════════════════════════════════════════╗"
echo "║      Working_Code Auto-Installer       ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "This script will add an alias to your shell configuration."
echo "Path identified: $RUNNER_PATH"
echo ""

# Alias naming
ALIAS_NAME="work"
echo "Alias to be added: $ALIAS_NAME"

# Select Shell
echo ""
echo "Select your shell:"
echo "1) Bash (.bashrc)"
echo "2) Zsh (.zshrc)"
echo "3) Fish (config.fish)"
echo "4) Sh (.profile)"
read -p "Number [1-4]: " SHELL_OPT

CONFIG_FILE=""
ALIAS_CMD=""
SHELL_NAME=""

case $SHELL_OPT in
    1)
        SHELL_NAME="Bash"
        CONFIG_FILE="$HOME/.bashrc"
        ALIAS_CMD="alias $ALIAS_NAME='$RUNNER_PATH'"
        ;;
    2)
        SHELL_NAME="Zsh"
        CONFIG_FILE="$HOME/.zshrc"
        ALIAS_CMD="alias $ALIAS_NAME='$RUNNER_PATH'"
        ;;
    3)
        SHELL_NAME="Fish"
        CONFIG_FILE="$HOME/.config/fish/config.fish"
        # Fish syntax compatible with recent versions, or universal function
        # Simple alias: alias name "command"
        ALIAS_CMD="alias $ALIAS_NAME '$RUNNER_PATH'"
        
        # Check if dir exists
        if [ ! -d "$HOME/.config/fish" ]; then
            echo "Warning: Fish config directory not found."
        fi
        ;;
    4)
        SHELL_NAME="Sh"
        CONFIG_FILE="$HOME/.profile"
        ALIAS_CMD="alias $ALIAS_NAME='$RUNNER_PATH'"
        ;;
    *)
        echo "Invalid option. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Target: $SHELL_NAME ($CONFIG_FILE)"
echo "Command to add: $ALIAS_CMD"
echo ""

# Check if file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file $CONFIG_FILE does not exist."
    read -p "Create it? (y/n): " CREATE_CONF
    if [[ "$CREATE_CONF" == "y" || "$CREATE_CONF" == "Y" ]]; then
        touch "$CONFIG_FILE"
    else
        echo "Aborted."
        exit 1
    fi
fi

# Check if alias already exists (simple grep)
if grep -q "$RUNNER_PATH" "$CONFIG_FILE"; then
    echo "Warning: It seems like $RUNNER_PATH is already referenced in $CONFIG_FILE."
    read -p "Add anyway? (y/n): " ADD_ANYWAY
    if [[ "$ADD_ANYWAY" != "y" && "$ADD_ANYWAY" != "Y" ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# Append
echo "" >> "$CONFIG_FILE"
echo "# Working_Code Alias" >> "$CONFIG_FILE"
echo "$ALIAS_CMD" >> "$CONFIG_FILE"

echo "✅ Successfully added alias '$ALIAS_NAME' to $CONFIG_FILE"
echo ""
echo "To use it immediately, run:"
if [ "$SHELL_NAME" == "Fish" ]; then
    echo "  source $CONFIG_FILE"
else
    echo "  source $CONFIG_FILE"
fi
echo "Then type '$ALIAS_NAME' to start."

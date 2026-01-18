#!/bin/bash

# Get the absolute path of the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Runner is now in scripts/
RUNNER_PATH="$SCRIPT_DIR/scripts/working_runner.sh"
BACKUP_DIR="$SCRIPT_DIR/backup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "╔════════════════════════════════════════╗"
echo -e "║      Working_Code Auto-Installer       ║"
echo -e "╚════════════════════════════════════════╝"
echo ""

# --- OS Detection & Dependency Check ---
echo -e "${BLUE}🔍 Detecting System...${NC}"

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo -e "  Detected: ${GREEN}macOS${NC}"
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed.${NC}"
        echo "Please install it using: brew install python"
        exit 1
    fi
elif [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$NAME
    ID=$ID
    echo -e "  Detected: ${GREEN}$DISTRO ($ID)${NC}"
    
    # Distro Specific Checks
    if [[ "$ID" == "arch" || "$ID" == "manjaro" ]]; then
        echo -e "${YELLOW}  -> Checking Arch/Manjaro dependencies...${NC}"
        if ! pacman -Qi python &> /dev/null; then
             echo -e "${RED}Warning: Python logic might fail if system is minimal.${NC}"
        fi
    elif [[ "$ID" == "debian" || "$ID" == "ubuntu" || "$ID" == "pop" ]]; then
        echo -e "${YELLOW}  -> Checking Debian/Ubuntu dependencies...${NC}"
        # specialized check for venv module which is often separate
        if ! dpkg -s python3-venv &> /dev/null; then
            echo -e "${RED}Warning: 'python3-venv' is likely missing.${NC}"
            echo -e "Please run: ${BLUE}sudo apt install python3-venv${NC}"
            read -p "Continue anyway? (y/n): " CONT
            if [[ "$CONT" != "y" ]]; then exit 1; fi
        fi
    elif [[ "$ID" == "fedora" ]]; then
         echo -e "${YELLOW}  -> Checking Fedora dependencies...${NC}"
         # Fedora usually comes with full python, but good to note
    fi
else
    echo -e "${YELLOW}Unknown Linux distribution. Proceeding with standard checks.${NC}"
fi

# Ensure the runner is executable
if [ -f "$RUNNER_PATH" ]; then
    chmod +x "$RUNNER_PATH"
else
    echo -e "${RED}Error: runner script not found at $RUNNER_PATH${NC}"
    exit 1
fi


# ------------------------------------------------------------------
# Language Selection
# ------------------------------------------------------------------
echo "--------------------------------------------------"
echo "Select Language / Seleccione Idioma / Choisissez la langue / Escolha o idioma"
echo "Options: ES, EN, FR, PT"
read -p "Language [Default: System Auto-detect]: " LANG_CHOICE
# Normalize input
if [[ -z "$LANG_CHOICE" ]]; then
    LANG_CHOICE="SYS"
else
    # Portable uppercase conversion (works on Bash 3.2/macOS)
    LANG_CHOICE=$(echo "$LANG_CHOICE" | tr '[:lower:]' '[:upper:]')
fi

# ------------------------------------------------------------------
# Environment Setup (VEnv + Dependencies)
# ------------------------------------------------------------------
VENV_DIR="$SCRIPT_DIR/venv"
echo ""
echo -e "${BLUE}📦 Initializing Python Environment in $VENV_DIR...${NC}"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing/Upgrading dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install rich typer google-generativeai openai --quiet

# ------------------------------------------------------------------
# Configure Language
# ------------------------------------------------------------------
if [[ "$LANG_CHOICE" =~ ^(ES|EN|FR|PT)$ ]]; then
    echo -e "${YELLOW}⚙️  Setting language to $LANG_CHOICE...${NC}"
    "$VENV_DIR/bin/python" "src/Working_Code.py" LANG-SET "$LANG_CHOICE"
else
    echo -e "${YELLOW}⚙️  Language set to System/Auto-detect.${NC}"
fi

echo ""
echo "Path identified: $RUNNER_PATH"
echo "Backup location: $BACKUP_DIR"
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
        ALIAS_CMD="alias $ALIAS_NAME '$RUNNER_PATH'"
        
        if [ ! -d "$HOME/.config/fish" ]; then
            echo -e "${YELLOW}Warning: Fish config directory not found.${NC}"
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
    echo -e "${YELLOW}Warning: It seems like $RUNNER_PATH is already referenced in $CONFIG_FILE.${NC}"
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

echo -e "${GREEN}✅ Successfully added alias '$ALIAS_NAME' to $CONFIG_FILE${NC}"
echo ""
echo "To use it immediately, run:"
echo -e "${BLUE}  source $CONFIG_FILE${NC}"
echo "Then type '$ALIAS_NAME' to start."


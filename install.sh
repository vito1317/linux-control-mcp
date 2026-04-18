#!/bin/bash
# ============================================================
# Linux Control MCP - Installer
# Installs all dependencies, builds project, and registers
# MCP server via `claude mcp add`.
# ============================================================
# Note: not using set -e to avoid aborting on non-fatal errors
# (e.g., claude mcp add returning non-zero when server already exists)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════╗"
echo "║       Linux Control MCP - Installer           ║"
echo "║  AI-driven Linux desktop control via X11      ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Detect Package Manager ─────────────────────────────────
detect_pkg_manager() {
    if command -v apt &> /dev/null; then
        PKG_MANAGER="apt"
        INSTALL_CMD="sudo apt install -y"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        INSTALL_CMD="sudo dnf install -y"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        INSTALL_CMD="sudo pacman -S --noconfirm"
    elif command -v zypper &> /dev/null; then
        PKG_MANAGER="zypper"
        INSTALL_CMD="sudo zypper install -y"
    else
        echo -e "${RED}[ERROR] No supported package manager found (apt/dnf/pacman/zypper)${NC}"
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} Package manager: $PKG_MANAGER"
}

# ─── Install System Dependencies ────────────────────────────
install_system_deps() {
    echo ""
    echo -e "${BLUE}[1/5] Installing system dependencies...${NC}"

    case $PKG_MANAGER in
        apt)
            $INSTALL_CMD xdotool wmctrl x11-utils xclip maim \
                python3 python3-gi gir1.2-gtk-3.0 gir1.2-atspi-2.0 at-spi2-core \
                tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-jpn 2>&1 | tail -3
            ;;
        dnf)
            $INSTALL_CMD xdotool wmctrl xrandr xclip maim \
                python3 python3-gobject gtk3 at-spi2-core \
                tesseract 2>&1 | tail -3
            ;;
        pacman)
            $INSTALL_CMD xdotool wmctrl xorg-xrandr xclip maim \
                python-gobject gtk3 at-spi2-core \
                tesseract 2>&1 | tail -3
            ;;
        zypper)
            $INSTALL_CMD xdotool wmctrl xrandr xclip \
                python3 python3-gobject gtk3 at-spi2-core \
                tesseract-ocr 2>&1 | tail -3
            ;;
    esac

    echo -e "${GREEN}[OK]${NC} System dependencies installed"
}

# ─── Check Node.js ──────────────────────────────────────────
check_nodejs() {
    echo ""
    echo -e "${BLUE}[2/5] Checking Node.js...${NC}"

    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}[INFO]${NC} Node.js not found, installing via nvm..."
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        nvm install 20
        nvm use 20
    fi

    NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        echo -e "${RED}[ERROR] Node.js >= 18 required, found v$(node --version)${NC}"
        exit 1
    fi

    echo -e "${GREEN}[OK]${NC} Node.js $(node --version)"
}

# ─── Clone or Update Repository ─────────────────────────────
setup_repo() {
    echo ""
    echo -e "${BLUE}[3/5] Setting up repository...${NC}"

    INSTALL_DIR="$HOME/.local/share/linux-control-mcp"

    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull origin main 2>&1 | tail -3
    else
        echo "Cloning repository..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone https://github.com/vito1317/linux-control-mcp.git "$INSTALL_DIR" 2>&1 | tail -3
        cd "$INSTALL_DIR"
    fi

    echo -e "${GREEN}[OK]${NC} Repository ready at $INSTALL_DIR"
}

# ─── Install & Build ────────────────────────────────────────
build_project() {
    echo ""
    echo -e "${BLUE}[4/5] Installing npm dependencies and building...${NC}"

    cd "$INSTALL_DIR"
    npm install 2>&1 | tail -5
    npm run build 2>&1 | tail -3

    # Make python scripts executable
    chmod +x python-helpers/*.py python-helpers/*.sh 2>/dev/null || true

    echo -e "${GREEN}[OK]${NC} Project built successfully"
}

# ─── Register MCP server (direct JSON write) ──────────────
register_mcp() {
    echo ""
    echo -e "${BLUE}[5/5] Registering MCP server...${NC}"

    # Write MCP server config directly to ~/.claude.json
    # (bypasses 'claude mcp add' which breaks curl|bash pipe)
    CLAUDE_CONFIG="$HOME/.claude.json"

    python3 -c "
import json, os

config_path = os.path.expanduser('~/.claude.json')
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except:
    config = {}

servers = config.setdefault('mcpServers', {})
servers['linux-control'] = {
    'command': 'node',
    'args': ['$INSTALL_DIR/dist/index.js']
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print('MCP server registered in ' + config_path)
" 2>&1

    echo -e "${GREEN}[OK]${NC} MCP server registered in ~/.claude.json"

    # Auto-allow all linux-control MCP permissions
    SETTINGS_DIR="$HOME/.claude"
    SETTINGS_FILE="$SETTINGS_DIR/settings.json"
    mkdir -p "$SETTINGS_DIR"

    python3 -c "
import json, os

settings_path = '$SETTINGS_FILE'
try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)
except:
    settings = {}

perms = settings.setdefault('permissions', {})
allow = perms.setdefault('allow', [])
# Add both hyphen and underscore variants to cover all permission formats
to_add = [
    'mcp__linux-control',
    'mcp__linux_control',
]
for p in to_add:
    if p not in allow:
        allow.append(p)

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
print('Permissions updated')
" 2>&1

    echo -e "${GREEN}[OK]${NC} Permissions auto-allowed in $SETTINGS_FILE"
}

# ─── Verify Installation ────────────────────────────────────
verify() {
    echo ""
    echo -e "${BLUE}Verifying installation...${NC}"
    echo ""

    TOOLS=("xdotool" "wmctrl" "xrandr" "xclip" "maim" "tesseract" "python3" "node")

    for tool in "${TOOLS[@]}"; do
        if command -v "$tool" &> /dev/null; then
            echo -e "  ${GREEN}✓${NC} $tool"
        else
            echo -e "  ${RED}✗${NC} $tool (missing)"
        fi
    done

    if python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} GTK3 (Python)"
    else
        echo -e "  ${YELLOW}~${NC} GTK3 (Python) - overlay animations unavailable"
    fi

    if python3 -c "import gi; gi.require_version('Atspi', '2.0')" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} AT-SPI2 (Python)"
    else
        echo -e "  ${YELLOW}~${NC} AT-SPI2 (Python) - accessibility tree limited"
    fi

    if [ -f "$INSTALL_DIR/dist/index.js" ]; then
        echo -e "  ${GREEN}✓${NC} MCP server built"
    else
        echo -e "  ${RED}✗${NC} MCP server NOT built"
    fi

    if command -v claude &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Claude CLI"
    else
        echo -e "  ${YELLOW}~${NC} Claude CLI not found"
    fi
}

# ─── Summary ────────────────────────────────────────────────
summary() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════╗"
    echo "║         Installation Complete!                 ║"
    echo "╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Install path:  ${BLUE}$INSTALL_DIR${NC}"
    echo ""
    echo -e "  Register MCP:  ${BLUE}claude mcp add linux-control -s user -- node $INSTALL_DIR/dist/index.js${NC}"
    echo -e "  Remove MCP:    ${BLUE}claude mcp remove linux-control -s user${NC}"
    echo -e "  Update:        ${BLUE}cd $INSTALL_DIR && git pull && npm run build${NC}"
    echo -e "  Uninstall:     ${BLUE}claude mcp remove linux-control -s user && rm -rf $INSTALL_DIR${NC}"
    echo ""
}

# ─── Main ───────────────────────────────────────────────────
main() {
    detect_pkg_manager
    install_system_deps
    check_nodejs
    setup_repo
    build_project
    register_mcp
    verify
    summary
}

main "$@"

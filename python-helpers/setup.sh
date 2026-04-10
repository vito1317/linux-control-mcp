#!/bin/bash
# Setup script for Linux Control MCP Python helpers
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Linux Control MCP - Python Helpers Setup ==="

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is required but not installed."
    exit 1
fi

echo "[OK] Python3 found: $(python3 --version)"

# Check required system tools
REQUIRED_TOOLS=("xdotool" "wmctrl" "xrandr" "xclip" "xprop")
MISSING_TOOLS=()

for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo ""
    echo "WARNING: The following tools are missing:"
    for tool in "${MISSING_TOOLS[@]}"; do
        echo "  - $tool"
    done
    echo ""
    echo "Install them with:"
    echo "  Ubuntu/Debian: sudo apt install ${MISSING_TOOLS[*]}"
    echo "  Fedora:        sudo dnf install ${MISSING_TOOLS[*]}"
    echo "  Arch:          sudo pacman -S ${MISSING_TOOLS[*]}"
    echo ""
fi

# Check screenshot tools (at least one needed)
SCREENSHOT_TOOLS=("maim" "scrot" "import")
HAS_SCREENSHOT=false
for tool in "${SCREENSHOT_TOOLS[@]}"; do
    if command -v "$tool" &> /dev/null; then
        echo "[OK] Screenshot tool found: $tool"
        HAS_SCREENSHOT=true
        break
    fi
done

if [ "$HAS_SCREENSHOT" = false ]; then
    echo "WARNING: No screenshot tool found. Install one of: maim, scrot, imagemagick"
    echo "  Ubuntu/Debian: sudo apt install maim"
fi

# Check optional tools
echo ""
echo "=== Optional Tools ==="

# Tesseract OCR
if command -v tesseract &> /dev/null; then
    echo "[OK] Tesseract OCR found (for ai_ocr_region)"
else
    echo "[--] Tesseract OCR not found (optional, for ai_ocr_region)"
    echo "     Install: sudo apt install tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-jpn"
fi

# GTK3 for overlay (check via python)
if python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null; then
    echo "[OK] GTK3 Python bindings found (for overlay animations)"
else
    echo "[--] GTK3 Python bindings not found (optional, for overlay animations)"
    echo "     Install: sudo apt install python3-gi gir1.2-gtk-3.0"
fi

# AT-SPI2 for accessibility
if python3 -c "import gi; gi.require_version('Atspi', '2.0')" 2>/dev/null; then
    echo "[OK] AT-SPI2 Python bindings found (for accessibility)"
else
    echo "[--] AT-SPI2 Python bindings not found (optional, for accessibility)"
    echo "     Install: sudo apt install python3-gi gir1.2-atspi-2.0 at-spi2-core"
fi

# Make Python scripts executable
chmod +x "$SCRIPT_DIR/linux_control.py"
chmod +x "$SCRIPT_DIR/overlay.py"
chmod +x "$SCRIPT_DIR/atspi_helper.py"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Required tools summary:"
for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v "$tool" &> /dev/null; then
        echo "  [OK] $tool"
    else
        echo "  [!!] $tool (MISSING)"
    fi
done
echo ""

# Quick install command for common distros
echo "Quick install (Ubuntu/Debian):"
echo "  sudo apt install xdotool wmctrl x11-utils xclip maim python3-gi gir1.2-gtk-3.0 gir1.2-atspi-2.0 at-spi2-core tesseract-ocr"
echo ""
echo "Quick install (Fedora):"
echo "  sudo dnf install xdotool wmctrl xrandr xclip maim python3-gobject gtk3 at-spi2-core tesseract"
echo ""
echo "Quick install (Arch):"
echo "  sudo pacman -S xdotool wmctrl xorg-xrandr xclip maim python-gobject gtk3 at-spi2-core tesseract"

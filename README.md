# Linux Control MCP

MCP (Model Context Protocol) server for AI-driven Linux desktop control via X11.

The Linux equivalent of [macos-control-mcp](../macos-control-mcp/), providing full desktop automation capabilities for AI agents on Linux systems.

## Features

**35 MCP Tools** across 8 categories:

| Category | Tools | Description |
|----------|-------|-------------|
| Mouse | 5 | move, click, drag, scroll, position |
| Keyboard | 3 | type (Unicode), press, hotkey |
| Screenshot | 3 | capture, annotate, screen info |
| Terminal | 3 | execute, background, script |
| Window | 6 | list, focus, resize, minimize, close, apps |
| Accessibility | 4 | check, tree, element_at, click |
| AI-Optimized | 6 | screen context, find element, OCR, screen elements, clipboard |
| Animation | 5 | click ripple, trail, typing, highlight, scroll |

## Architecture

```
┌─────────────────────────────┐
│   AI Agent (Claude, etc.)   │
└─────────┬───────────────────┘
          │ MCP Protocol (stdio)
┌─────────▼───────────────────┐
│  TypeScript MCP Server      │
│  (Node.js + Sharp + Zod)    │
└─────────┬───────────────────┘
          │ child_process
┌─────────▼───────────────────┐     ┌──────────────────────┐
│  Python Helper               │     │  Overlay Process     │
│  (xdotool, wmctrl, xrandr)  │     │  (GTK3 + Cairo)      │
└─────────┬───────────────────┘     └──────────────────────┘
          │
┌─────────▼───────────────────┐
│  X11 / Linux Desktop        │
└─────────────────────────────┘
```

## Prerequisites

### Required
- Node.js >= 18
- Python 3.8+
- X11 display server
- `xdotool` - mouse/keyboard/window control
- `wmctrl` - window management
- `xrandr` - screen information
- `xclip` - clipboard access
- `xprop` - window properties

### Screenshot (at least one)
- `maim` (recommended)
- `scrot`
- `imagemagick` (import command)

### Optional
- `tesseract-ocr` - OCR for ai_ocr_region
- `python3-gi` + `gir1.2-gtk-3.0` - overlay animations
- `gir1.2-atspi-2.0` + `at-spi2-core` - full accessibility tree

## Quick Install

**Ubuntu/Debian:**
```bash
sudo apt install xdotool wmctrl x11-utils xclip maim \
  python3-gi gir1.2-gtk-3.0 gir1.2-atspi-2.0 at-spi2-core \
  tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-jpn
```

**Fedora:**
```bash
sudo dnf install xdotool wmctrl xrandr xclip maim \
  python3-gobject gtk3 at-spi2-core tesseract
```

**Arch Linux:**
```bash
sudo pacman -S xdotool wmctrl xorg-xrandr xclip maim \
  python-gobject gtk3 at-spi2-core tesseract
```

## One-Click Install

```bash
curl -fsSL https://raw.githubusercontent.com/vito1317/linux-control-mcp/main/install.sh | bash
```

This will automatically install dependencies, build the project, and register the MCP server.

## Manual Install

```bash
# Clone
git clone https://github.com/vito1317/linux-control-mcp.git ~/.local/share/linux-control-mcp
cd ~/.local/share/linux-control-mcp

# Install system dependencies (Ubuntu/Debian)
sudo apt install xdotool wmctrl x11-utils xclip maim python3-gi gir1.2-gtk-3.0 gir1.2-atspi-2.0

# Build
npm install && npm run build

# Register MCP
claude mcp add linux-control -- node ~/.local/share/linux-control-mcp/dist/index.js
```

## Usage

```bash
# Register
claude mcp add linux-control -- node ~/.local/share/linux-control-mcp/dist/index.js

# Remove
claude mcp remove linux-control

# Update
cd ~/.local/share/linux-control-mcp && git pull && npm run build

# Uninstall
claude mcp remove linux-control && rm -rf ~/.local/share/linux-control-mcp
```

## Tool Reference

### Mouse Tools
- `mouse_move` - Move cursor to (x, y)
- `mouse_click` - Click at (x, y) with button (left/right/middle) and click count
- `mouse_drag` - Drag from (x1, y1) to (x2, y2)
- `mouse_scroll` - Scroll at (x, y) with deltaX/deltaY
- `mouse_position` - Get current cursor position

### Keyboard Tools
- `keyboard_type` - Type text (supports Unicode/CJK)
- `keyboard_press` - Press key with modifiers
- `keyboard_hotkey` - Press key combo (e.g., "ctrl+c")

### Screenshot Tools
- `screenshot` - Capture screen with optional grid overlay and region
- `screenshot_annotated` - Capture and mark points with labels
- `screen_info` - Get display resolution, scale, position

### Terminal Tools
- `terminal_execute` - Run shell command with timeout
- `terminal_execute_background` - Start background process
- `terminal_script` - Execute shell script

### Window Tools
- `window_list` - List all visible windows
- `window_focus` - Activate window by app name
- `window_resize` - Move/resize window
- `window_minimize` - Minimize window
- `window_close` - Close window
- `apps_list` - List running GUI applications

### Accessibility Tools
- `accessibility_check` - Check AT-SPI2 availability
- `accessibility_tree` - Get UI element tree
- `accessibility_element_at` - Get element at coordinates
- `accessibility_click` - Click element by role/title

### AI-Optimized Tools
- `ai_screen_context` - Combined screenshot + accessibility + mouse position
- `ai_find_element` - Natural language element search
- `ai_ocr_region` - Extract text from screen region (Tesseract)
- `ai_screen_elements` - Screenshot with numbered element markers
- `clipboard_read` - Read clipboard
- `clipboard_write` - Write to clipboard

### Animation Tools
- `animation_click` - Show click ripple effect
- `animation_trail` - Show mouse movement trail
- `animation_type` - Show typing indicator
- `animation_highlight` - Show pulsing highlight box
- `animation_scroll` - Show scroll direction indicator

## License

MIT

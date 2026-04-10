#!/usr/bin/env python3
"""
Linux Control Helper - Native X11 desktop control for AI agents.
Replaces macOS Swift helpers with Linux equivalents using:
- xdotool for mouse/keyboard/window control
- xrandr for screen info
- wmctrl for window management
- scrot/maim for screenshots
- xclip for clipboard
- AT-SPI2 for accessibility
"""

import sys
import json
import subprocess
import os
import time
import re
import struct
import signal
from typing import Any, Optional

# ─── JSON Output Helpers ────────────────────────────────────────────────

def json_output(data: dict):
    """Print JSON and exit."""
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0)

def json_error(msg: str):
    json_output({"success": False, "error": msg})

def json_success(data: dict):
    data["success"] = True
    json_output(data)

def run_cmd(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a command and return result."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        json_error(f"Command not found: {cmd[0]}. Please install it.")
    except subprocess.TimeoutExpired:
        json_error(f"Command timed out: {' '.join(cmd)}")

def run_cmd_output(cmd: list[str], timeout: int = 10) -> str:
    """Run command and return stdout."""
    result = run_cmd(cmd, timeout)
    return result.stdout.strip() if result else ""

# ─── Mouse Control ──────────────────────────────────────────────────────

def mouse_move(x: int, y: int):
    """Move mouse to absolute position."""
    run_cmd(["xdotool", "mousemove", str(x), str(y)])
    json_success({"action": "mouse_move", "x": x, "y": y})

def mouse_click(x: int, y: int, button: str = "left", clicks: int = 1):
    """Click mouse at position."""
    button_map = {"left": "1", "middle": "2", "right": "3"}
    btn = button_map.get(button, "1")

    # Move to position first
    run_cmd(["xdotool", "mousemove", str(x), str(y)])

    # Perform click(s)
    for _ in range(clicks):
        run_cmd(["xdotool", "click", btn])

    json_success({
        "action": "mouse_click",
        "x": x, "y": y,
        "button": button,
        "clicks": clicks
    })

def mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5):
    """Drag from one position to another."""
    # Move to start
    run_cmd(["xdotool", "mousemove", "--sync", str(from_x), str(from_y)])
    time.sleep(0.05)

    # Press, move, release
    run_cmd(["xdotool", "mousedown", "1"])

    # Interpolate movement
    steps = max(10, int(duration * 60))
    for i in range(1, steps + 1):
        t = i / steps
        cx = int(from_x + (to_x - from_x) * t)
        cy = int(from_y + (to_y - from_y) * t)
        run_cmd(["xdotool", "mousemove", "--sync", str(cx), str(cy)])
        time.sleep(duration / steps)

    run_cmd(["xdotool", "mouseup", "1"])

    json_success({
        "action": "mouse_drag",
        "from": {"x": from_x, "y": from_y},
        "to": {"x": to_x, "y": to_y},
        "duration": duration
    })

def mouse_scroll(x: int, y: int, delta_x: int = 0, delta_y: int = 0):
    """Scroll at position. delta_y: positive=up, negative=down."""
    run_cmd(["xdotool", "mousemove", str(x), str(y)])

    if delta_y != 0:
        # xdotool: button 4=scroll up, 5=scroll down
        btn = "4" if delta_y > 0 else "5"
        for _ in range(abs(delta_y)):
            run_cmd(["xdotool", "click", btn])

    if delta_x != 0:
        # button 6=scroll left, 7=scroll right
        btn = "7" if delta_x > 0 else "6"
        for _ in range(abs(delta_x)):
            run_cmd(["xdotool", "click", btn])

    json_success({
        "action": "mouse_scroll",
        "x": x, "y": y,
        "deltaX": delta_x, "deltaY": delta_y
    })

def mouse_position():
    """Get current mouse position."""
    output = run_cmd_output(["xdotool", "getmouselocation"])
    # Output: "x:123 y:456 screen:0 window:12345"
    match = re.search(r'x:(\d+)\s+y:(\d+)', output)
    if match:
        x, y = int(match.group(1)), int(match.group(2))
        json_success({"action": "mouse_position", "x": x, "y": y})
    else:
        json_error("Failed to get mouse position")

# ─── Keyboard Control ───────────────────────────────────────────────────

# xdotool key name mapping
KEY_MAP = {
    "return": "Return", "enter": "Return",
    "tab": "Tab", "escape": "Escape", "esc": "Escape",
    "space": "space", "backspace": "BackSpace", "delete": "Delete",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "home": "Home", "end": "End", "pageup": "Prior", "pagedown": "Next",
    "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4",
    "f5": "F5", "f6": "F6", "f7": "F7", "f8": "F8",
    "f9": "F9", "f10": "F10", "f11": "F11", "f12": "F12",
    "volumeup": "XF86AudioRaiseVolume",
    "volumedown": "XF86AudioLowerVolume",
    "mute": "XF86AudioMute",
    "brightnessup": "XF86MonBrightnessUp",
    "brightnessdown": "XF86MonBrightnessDown",
    "printscreen": "Print",
    "insert": "Insert",
    "capslock": "Caps_Lock",
    "numlock": "Num_Lock",
    "scrolllock": "Scroll_Lock",
    "pause": "Pause",
    "menu": "Menu",
}

MODIFIER_MAP = {
    "ctrl": "ctrl", "control": "ctrl",
    "alt": "alt", "option": "alt",
    "shift": "shift",
    "super": "super", "cmd": "super", "command": "super", "meta": "super",
}

def keyboard_type(text: str):
    """Type text string (supports Unicode)."""
    # xdotool type supports --clearmodifiers to avoid modifier interference
    run_cmd(["xdotool", "type", "--clearmodifiers", "--delay", "50", text])
    json_success({"action": "keyboard_type", "text": text, "length": len(text)})

def keyboard_press(key: str, modifiers: list[str] = None):
    """Press a single key with optional modifiers."""
    modifiers = modifiers or []

    # Map key name
    mapped_key = KEY_MAP.get(key.lower(), key)

    # Build key combo
    parts = []
    for mod in modifiers:
        mapped_mod = MODIFIER_MAP.get(mod.lower(), mod)
        parts.append(mapped_mod)
    parts.append(mapped_key)

    combo = "+".join(parts)
    run_cmd(["xdotool", "key", "--clearmodifiers", combo])

    json_success({
        "action": "keyboard_press",
        "key": key,
        "modifiers": modifiers
    })

def keyboard_hotkey(keys: str):
    """Press a hotkey combination like 'ctrl+c', 'ctrl+shift+s'."""
    parts = [k.strip() for k in keys.split("+")]
    if len(parts) == 1:
        keyboard_press(parts[0])
        return

    modifiers = parts[:-1]
    key = parts[-1]
    keyboard_press(key, modifiers)

# ─── Screen Info ────────────────────────────────────────────────────────

def screen_info():
    """Get display information using xrandr."""
    output = run_cmd_output(["xrandr", "--query"])
    screens = []
    idx = 0

    for line in output.split("\n"):
        # Match connected displays with resolution
        match = re.match(
            r'^(\S+)\s+connected\s+(?:primary\s+)?(\d+)x(\d+)\+(\d+)\+(\d+)',
            line
        )
        if match:
            name = match.group(1)
            w, h = int(match.group(2)), int(match.group(3))
            x, y = int(match.group(4)), int(match.group(5))
            is_primary = "primary" in line

            # Try to get scale factor from xrandr
            scale = 1.0
            scale_match = re.search(r'(\d+)x(\d+)\+\d+\+\d+', line)

            screens.append({
                "index": idx,
                "name": name,
                "isMain": is_primary,
                "frame": {"x": x, "y": y, "width": w, "height": h},
                "visibleFrame": {"x": x, "y": y, "width": w, "height": h},
                "scaleFactor": scale
            })
            idx += 1

    if not screens:
        # Fallback: use xdpyinfo
        output2 = run_cmd_output(["xdpyinfo"])
        dim_match = re.search(r'dimensions:\s+(\d+)x(\d+)', output2)
        if dim_match:
            w, h = int(dim_match.group(1)), int(dim_match.group(2))
            screens.append({
                "index": 0, "name": "default", "isMain": True,
                "frame": {"x": 0, "y": 0, "width": w, "height": h},
                "visibleFrame": {"x": 0, "y": 0, "width": w, "height": h},
                "scaleFactor": 1.0
            })

    json_success({"action": "screen_info", "count": len(screens), "screens": screens})

# ─── Window Management ──────────────────────────────────────────────────

def window_list():
    """List all visible windows."""
    output = run_cmd_output(["wmctrl", "-l", "-p", "-G"])
    windows = []

    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 9)
        if len(parts) < 9:
            continue

        wid = parts[0]
        desktop = parts[1]
        pid = int(parts[2]) if parts[2].isdigit() else 0
        x, y = int(parts[3]), int(parts[4])
        w, h = int(parts[5]), int(parts[6])
        hostname = parts[7]
        title = parts[8] if len(parts) > 8 else ""

        # Get window class (app name)
        class_output = run_cmd_output(["xprop", "-id", wid, "WM_CLASS"])
        app_name = ""
        class_match = re.search(r'"([^"]+)"\s*,\s*"([^"]+)"', class_output)
        if class_match:
            app_name = class_match.group(2)  # Use class name

        windows.append({
            "windowID": int(wid, 16) if wid.startswith("0x") else int(wid),
            "windowIDHex": wid,
            "ownerName": app_name or hostname,
            "windowName": title,
            "pid": pid,
            "bounds": {"X": x, "Y": y, "Width": w, "Height": h},
            "alpha": 1,
            "desktop": int(desktop) if desktop != "-1" else -1
        })

    json_success({"action": "window_list", "count": len(windows), "windows": windows})

def window_focus(app_name: str):
    """Activate a window by app name (case-insensitive partial match)."""
    output = run_cmd_output(["wmctrl", "-l"])
    target_lower = app_name.lower()

    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        wid = parts[0]
        title = parts[3] if len(parts) > 3 else ""

        # Check window class too
        class_output = run_cmd_output(["xprop", "-id", wid, "WM_CLASS"])
        class_match = re.search(r'"([^"]+)"\s*,\s*"([^"]+)"', class_output)
        class_name = class_match.group(2).lower() if class_match else ""
        instance_name = class_match.group(1).lower() if class_match else ""

        if (target_lower in title.lower() or
            target_lower in class_name or
            target_lower in instance_name):
            run_cmd(["wmctrl", "-i", "-a", wid])
            json_success({
                "action": "window_focus",
                "app": app_name,
                "windowID": wid,
                "title": title
            })
            return

    # Fallback: try xdotool
    output2 = run_cmd_output(["xdotool", "search", "--name", app_name])
    if output2:
        wid = output2.split("\n")[0]
        run_cmd(["xdotool", "windowactivate", wid])
        json_success({"action": "window_focus", "app": app_name, "windowID": wid})
        return

    json_error(f"Window not found: {app_name}")

def window_resize(app_name: str, x: int, y: int, width: int, height: int):
    """Move and resize a window."""
    output = run_cmd_output(["xdotool", "search", "--name", app_name])
    if not output:
        json_error(f"Window not found: {app_name}")
        return

    wid = output.split("\n")[0]
    run_cmd(["xdotool", "windowmove", wid, str(x), str(y)])
    run_cmd(["xdotool", "windowsize", wid, str(width), str(height)])

    json_success({
        "action": "window_resize",
        "app": app_name,
        "x": x, "y": y, "width": width, "height": height
    })

def window_minimize(app_name: str = ""):
    """Minimize a window."""
    if app_name:
        output = run_cmd_output(["xdotool", "search", "--name", app_name])
        if output:
            wid = output.split("\n")[0]
            run_cmd(["xdotool", "windowminimize", wid])
    else:
        wid = run_cmd_output(["xdotool", "getactivewindow"])
        if wid:
            run_cmd(["xdotool", "windowminimize", wid])

    json_success({"action": "window_minimize", "app": app_name or "active"})

def window_close(app_name: str = ""):
    """Close a window."""
    if app_name:
        output = run_cmd_output(["xdotool", "search", "--name", app_name])
        if output:
            wid = output.split("\n")[0]
            run_cmd(["wmctrl", "-i", "-c", wid])
    else:
        wid = run_cmd_output(["xdotool", "getactivewindow"])
        if wid:
            run_cmd(["wmctrl", "-i", "-c", f"0x{int(wid):08x}"])

    json_success({"action": "window_close", "app": app_name or "active"})

# ─── Applications ───────────────────────────────────────────────────────

def apps_list():
    """List running GUI applications."""
    apps = {}
    output = run_cmd_output(["wmctrl", "-l", "-p"])

    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 4)
        if len(parts) < 3:
            continue
        wid = parts[0]
        pid = int(parts[2]) if parts[2].isdigit() else 0
        if pid == 0:
            continue

        class_output = run_cmd_output(["xprop", "-id", wid, "WM_CLASS"])
        class_match = re.search(r'"([^"]+)"\s*,\s*"([^"]+)"', class_output)
        if class_match:
            app_name = class_match.group(2)
            if app_name not in apps:
                # Check if active
                active_wid = run_cmd_output(["xdotool", "getactivewindow"])
                is_active = False
                try:
                    is_active = int(active_wid) == int(wid, 16)
                except:
                    pass

                apps[app_name] = {
                    "name": app_name,
                    "pid": pid,
                    "bundleID": class_match.group(1),
                    "isActive": is_active,
                    "isHidden": False
                }

    app_list = list(apps.values())
    json_success({"action": "apps_list", "count": len(app_list), "apps": app_list})

# ─── Clipboard ──────────────────────────────────────────────────────────

def clipboard_read():
    """Read clipboard contents."""
    text = run_cmd_output(["xclip", "-selection", "clipboard", "-o"])
    json_success({"action": "clipboard_read", "text": text})

def clipboard_write(text: str):
    """Write text to clipboard."""
    proc = subprocess.Popen(
        ["xclip", "-selection", "clipboard"],
        stdin=subprocess.PIPE
    )
    proc.communicate(input=text.encode("utf-8"))
    json_success({"action": "clipboard_write", "text": text, "length": len(text)})

# ─── Accessibility (AT-SPI2) ────────────────────────────────────────────

def accessibility_check():
    """Check if AT-SPI2 accessibility is available."""
    try:
        result = run_cmd(["python3", "-c", "import atspi; print('ok')"])
        if result and result.returncode == 0:
            json_success({"action": "accessibility_check", "enabled": True, "method": "atspi"})
            return
    except:
        pass

    # Try dbus check
    result2 = run_cmd(["dbus-send", "--session", "--print-reply",
                        "--dest=org.a11y.Bus",
                        "/org/a11y/bus", "org.freedesktop.DBus.Peer.Ping"])
    if result2 and result2.returncode == 0:
        json_success({"action": "accessibility_check", "enabled": True, "method": "dbus"})
    else:
        json_success({"action": "accessibility_check", "enabled": False,
                       "error": "AT-SPI2 not available. Install python3-atspi2 or at-spi2-core."})

def accessibility_tree(pid: Optional[int] = None, max_depth: int = 3):
    """Get accessibility tree using AT-SPI2 via helper script."""
    script = os.path.join(os.path.dirname(__file__), "atspi_helper.py")

    if not os.path.exists(script):
        # Fallback: use xprop/xdotool based tree
        _accessibility_tree_fallback(pid, max_depth)
        return

    args = ["python3", script, "tree"]
    if pid:
        args.extend(["--pid", str(pid)])
    args.extend(["--depth", str(max_depth)])

    result = run_cmd(args, timeout=15)
    if result and result.returncode == 0 and result.stdout.strip():
        # Forward atspi_helper's JSON output directly to avoid double-serialization
        print(result.stdout.strip())
        return
    _accessibility_tree_fallback(pid, max_depth)

def _accessibility_tree_fallback(pid: Optional[int], max_depth: int):
    """Fallback accessibility tree using xprop and xwininfo."""
    # Get active window if no pid
    if pid:
        output = run_cmd_output(["xdotool", "search", "--pid", str(pid)])
        wid = output.split("\n")[0] if output else ""
    else:
        wid = run_cmd_output(["xdotool", "getactivewindow"])

    if not wid:
        json_error("No active window found")
        return

    # Get window properties
    name_output = run_cmd_output(["xdotool", "getwindowname", wid])
    geo_output = run_cmd_output(["xdotool", "getwindowgeometry", wid])

    # Parse geometry
    geo_match = re.search(r'Position:\s+(\d+),(\d+).*?Geometry:\s+(\d+)x(\d+)',
                           geo_output, re.DOTALL)
    pos_x, pos_y, width, height = 0, 0, 0, 0
    if geo_match:
        pos_x, pos_y = int(geo_match.group(1)), int(geo_match.group(2))
        width, height = int(geo_match.group(3)), int(geo_match.group(4))

    tree = {
        "role": "AXWindow",
        "title": name_output,
        "position": {"x": pos_x, "y": pos_y},
        "size": {"width": width, "height": height},
        "children": []
    }

    json_success({
        "action": "accessibility_tree",
        "tree": tree,
        "method": "xdotool-fallback",
        "note": "Install python3-atspi2 for full accessibility tree support"
    })

def accessibility_element_at(x: int, y: int):
    """Get UI element at screen coordinates."""
    script = os.path.join(os.path.dirname(__file__), "atspi_helper.py")

    if os.path.exists(script):
        result = run_cmd(["python3", script, "element_at", str(x), str(y)], timeout=10)
        if result and result.returncode == 0 and result.stdout.strip():
            # Forward atspi_helper's JSON output directly
            print(result.stdout.strip())
            return

    # Fallback
    wid = run_cmd_output(["xdotool", "getmouselocation", "--shell"])
    window_match = re.search(r'WINDOW=(\d+)', wid)
    if window_match:
        window_id = window_match.group(1)
        name = run_cmd_output(["xdotool", "getwindowname", window_id])
        json_success({
            "action": "element_at",
            "x": x, "y": y,
            "element": {"role": "AXWindow", "title": name, "windowID": window_id},
            "method": "xdotool-fallback"
        })
    else:
        json_error("No element found at position")

def accessibility_click(role: str, title: str = "", pid: Optional[int] = None):
    """Click an accessibility element by role and title."""
    script = os.path.join(os.path.dirname(__file__), "atspi_helper.py")

    if os.path.exists(script):
        args = ["python3", script, "click", "--role", role]
        if title:
            args.extend(["--title", title])
        if pid:
            args.extend(["--pid", str(pid)])

        result = run_cmd(args, timeout=10)
        if result and result.returncode == 0 and result.stdout.strip():
            print(result.stdout.strip())
            return

    json_error("Accessibility click requires python3-atspi2. Use mouse_click as fallback.")

# ─── Focused Element Position ───────────────────────────────────────────

def focused_position():
    """Get the position of the currently focused UI element."""
    script = os.path.join(os.path.dirname(__file__), "atspi_helper.py")

    if os.path.exists(script):
        result = run_cmd(["python3", script, "focused_position"], timeout=5)
        if result and result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                json_success(data)
                return
            except:
                pass

    # Fallback: use xdotool to get active window position
    wid = run_cmd_output(["xdotool", "getactivewindow"])
    if wid:
        geo = run_cmd_output(["xdotool", "getwindowgeometry", wid])
        match = re.search(r'Position:\s+(\d+),(\d+).*?Geometry:\s+(\d+)x(\d+)', geo, re.DOTALL)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            w, h = int(match.group(3)), int(match.group(4))
            json_success({
                "action": "focused_position",
                "source": "window-center",
                "x": x + w // 2, "y": y + h // 2,
                "width": w, "height": h,
                "app": run_cmd_output(["xdotool", "getwindowname", wid])
            })
            return

    json_error("Could not determine focused element position")

def accessibility_find(query: str):
    """Find UI elements matching a natural language query by searching the accessibility tree."""
    script = os.path.join(os.path.dirname(__file__), "atspi_helper.py")

    if not os.path.exists(script):
        json_error("accessibility find requires atspi_helper.py")
        return

    # Get the full accessibility tree
    result = run_cmd(["python3", script, "tree", "--depth", "5"], timeout=15)
    if not result or result.returncode != 0 or not result.stdout.strip():
        json_error("Failed to get accessibility tree for search")
        return

    try:
        tree_data = json.loads(result.stdout)
    except:
        json_error("Failed to parse accessibility tree")
        return

    query_lower = query.lower()
    matches = []

    def search_node(node, depth=0):
        if not isinstance(node, dict):
            return
        title = node.get("title", "")
        role = node.get("role", "")
        desc = node.get("description", "")
        searchable = f"{title} {role} {desc}".lower()
        if query_lower in searchable:
            match = {"role": role, "title": title, "description": desc}
            if "position" in node:
                match["position"] = node["position"]
            if "size" in node:
                match["size"] = node["size"]
            matches.append(match)
        for child in node.get("children", []):
            search_node(child, depth + 1)

    tree = tree_data.get("tree", tree_data)
    search_node(tree)

    json_success({
        "action": "accessibility_find",
        "query": query,
        "matches": matches,
        "count": len(matches)
    })

# ─── Screenshot ─────────────────────────────────────────────────────────

def screenshot(filepath: str, region: Optional[dict] = None, window_id: Optional[int] = None):
    """Take a screenshot."""
    if window_id:
        # Capture specific window
        run_cmd(["import", "-window", str(window_id), filepath])
    elif region:
        x, y = region.get("x", 0), region.get("y", 0)
        w, h = region.get("width", 100), region.get("height", 100)
        geometry = f"{w}x{h}+{x}+{y}"

        # Try maim first, fallback to scrot, then import
        result = run_cmd(["maim", "-g", geometry, filepath])
        if not result or result.returncode != 0:
            result = run_cmd(["scrot", "-a", f"{x},{y},{w},{h}", filepath])
            if not result or result.returncode != 0:
                run_cmd(["import", "-crop", geometry, "-window", "root", filepath])
    else:
        # Full screen
        result = run_cmd(["maim", filepath])
        if not result or result.returncode != 0:
            result = run_cmd(["scrot", filepath])
            if not result or result.returncode != 0:
                run_cmd(["import", "-window", "root", filepath])

    if os.path.exists(filepath):
        json_success({
            "action": "screenshot",
            "path": filepath,
            "size": os.path.getsize(filepath)
        })
    else:
        json_error("Screenshot failed - no output file created")

# ─── OCR ────────────────────────────────────────────────────────────────

def ocr_region(x: int, y: int, width: int, height: int):
    """Extract text from a screen region using tesseract."""
    import tempfile
    tmpfile = tempfile.mktemp(suffix=".png")

    # Take screenshot of region
    geometry = f"{width}x{height}+{x}+{y}"
    result = run_cmd(["maim", "-g", geometry, tmpfile])
    if not result or result.returncode != 0:
        run_cmd(["import", "-crop", geometry, "-window", "root", tmpfile])

    if not os.path.exists(tmpfile):
        json_error("Failed to capture region for OCR")
        return

    # Run tesseract
    result = run_cmd(["tesseract", tmpfile, "stdout", "-l", "eng+chi_tra+chi_sim+jpn"])
    if result and result.returncode == 0:
        text = result.stdout.strip()
        os.unlink(tmpfile)
        json_success({
            "action": "ocr_region",
            "text": text,
            "region": {"x": x, "y": y, "width": width, "height": height}
        })
    else:
        os.unlink(tmpfile) if os.path.exists(tmpfile) else None
        json_error("OCR failed. Install tesseract-ocr.")

# ─── CLI Dispatcher ─────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        json_error(f"Usage: {sys.argv[0]} <command> <subcommand> [args...]")
        return

    command = sys.argv[1]
    subcommand = sys.argv[2]
    args = sys.argv[3:]

    # Detect Wayland session
    is_wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY")
    wayland_helper = os.path.join(os.path.dirname(__file__), "wayland_input.py")
    use_wayland = is_wayland and os.path.exists(wayland_helper)

    try:
        # On Wayland, route keyboard/mouse input through wayland_input.py
        if use_wayland and command == "keyboard":
            if subcommand == "type":
                result = run_cmd(["python3", wayland_helper, "type", args[0] if args else ""], timeout=15)
                if result and result.stdout.strip():
                    print(result.stdout.strip())
                else:
                    json_error("Wayland keyboard type failed")
                return
            elif subcommand == "press":
                key = args[0] if args else ""
                mods = args[1] if len(args) > 1 and args[1] else ""
                result = run_cmd(["python3", wayland_helper, "press", key, mods], timeout=10)
                if result and result.stdout.strip():
                    print(result.stdout.strip())
                else:
                    json_error("Wayland keyboard press failed")
                return
            elif subcommand == "hotkey":
                result = run_cmd(["python3", wayland_helper, "hotkey", args[0] if args else ""], timeout=10)
                if result and result.stdout.strip():
                    print(result.stdout.strip())
                else:
                    json_error("Wayland hotkey failed")
                return

        if use_wayland and command == "mouse":
            if subcommand == "click":
                x, y = int(args[0]), int(args[1])
                button = args[2] if len(args) > 2 else "left"
                clicks = int(args[3]) if len(args) > 3 else 1
                # Move mouse with xdotool (still works for Xwayland position tracking)
                run_cmd(["xdotool", "mousemove", str(x), str(y)])
                time.sleep(0.05)
                for _ in range(clicks):
                    result = run_cmd(["python3", wayland_helper, "click", button], timeout=10)
                    time.sleep(0.05)
                json_success({"action": "mouse_click", "x": x, "y": y, "button": button, "clicks": clicks})
                return
            elif subcommand == "scroll":
                x, y = int(args[0]), int(args[1])
                dy = int(args[2]) if len(args) > 2 else 0
                dx = int(args[3]) if len(args) > 3 else 0
                run_cmd(["xdotool", "mousemove", str(x), str(y)])
                time.sleep(0.05)
                result = run_cmd(["python3", wayland_helper, "scroll", str(dy), str(dx)], timeout=10)
                if result and result.stdout.strip():
                    print(result.stdout.strip())
                else:
                    json_error("Wayland scroll failed")
                return

        if command == "mouse":
            if subcommand == "move":
                mouse_move(int(args[0]), int(args[1]))
            elif subcommand == "click":
                x, y = int(args[0]), int(args[1])
                button = args[2] if len(args) > 2 else "left"
                clicks = int(args[3]) if len(args) > 3 else 1
                mouse_click(x, y, button, clicks)
            elif subcommand == "drag":
                mouse_drag(int(args[0]), int(args[1]), int(args[2]), int(args[3]),
                           float(args[4]) if len(args) > 4 else 0.5)
            elif subcommand == "scroll":
                mouse_scroll(int(args[0]), int(args[1]),
                             int(args[2]) if len(args) > 2 else 0,
                             int(args[3]) if len(args) > 3 else 0)
            elif subcommand == "position":
                mouse_position()
            else:
                json_error(f"Unknown mouse subcommand: {subcommand}")

        elif command == "keyboard":
            if subcommand == "type":
                keyboard_type(args[0] if args else "")
            elif subcommand == "press":
                key = args[0] if args else ""
                mods = args[1].split(",") if len(args) > 1 and args[1] else []
                keyboard_press(key, mods)
            elif subcommand == "hotkey":
                keyboard_hotkey(args[0] if args else "")
            else:
                json_error(f"Unknown keyboard subcommand: {subcommand}")

        elif command == "screen":
            if subcommand == "info":
                screen_info()
            elif subcommand == "screenshot":
                filepath = args[0] if args else "/tmp/screenshot.png"
                region = None
                if len(args) > 4:
                    region = {"x": int(args[1]), "y": int(args[2]),
                              "width": int(args[3]), "height": int(args[4])}
                window_id = int(args[5]) if len(args) > 5 else None
                screenshot(filepath, region, window_id)
            elif subcommand == "ocr":
                ocr_region(int(args[0]), int(args[1]), int(args[2]), int(args[3]))
            else:
                json_error(f"Unknown screen subcommand: {subcommand}")

        elif command == "window":
            if subcommand == "list":
                window_list()
            elif subcommand == "focus":
                window_focus(args[0] if args else "")
            elif subcommand == "resize":
                window_resize(args[0], int(args[1]), int(args[2]), int(args[3]), int(args[4]))
            elif subcommand == "minimize":
                window_minimize(args[0] if args else "")
            elif subcommand == "close":
                window_close(args[0] if args else "")
            else:
                json_error(f"Unknown window subcommand: {subcommand}")

        elif command == "apps":
            if subcommand == "list":
                apps_list()
            else:
                json_error(f"Unknown apps subcommand: {subcommand}")

        elif command == "clipboard":
            if subcommand == "read":
                clipboard_read()
            elif subcommand == "write":
                clipboard_write(args[0] if args else "")
            else:
                json_error(f"Unknown clipboard subcommand: {subcommand}")

        elif command == "terminal":
            if subcommand == "execute" or subcommand == "script":
                cmd_str = args[0] if args else ""
                cwd = None
                shell = "/bin/bash"
                timeout_ms = 30000
                env_vars = {}
                i = 1
                while i < len(args):
                    if args[i] == "--cwd" and i + 1 < len(args):
                        cwd = args[i + 1]; i += 2
                    elif args[i] == "--shell" and i + 1 < len(args):
                        shell = args[i + 1]; i += 2
                    elif args[i] == "--timeout" and i + 1 < len(args):
                        timeout_ms = int(args[i + 1]); i += 2
                    elif args[i] == "--env" and i + 1 < len(args):
                        env_vars = json.loads(args[i + 1]); i += 2
                    else:
                        i += 1
                env = os.environ.copy()
                env.update(env_vars)
                try:
                    result = subprocess.run(
                        cmd_str, shell=True, executable=shell,
                        capture_output=True, text=True,
                        cwd=cwd, env=env,
                        timeout=timeout_ms / 1000
                    )
                    json_success({
                        "action": "terminal_execute",
                        "command": cmd_str,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "exitCode": result.returncode
                    })
                except subprocess.TimeoutExpired:
                    json_error(f"Command timed out after {timeout_ms}ms: {cmd_str}")
            elif subcommand == "background":
                cmd_str = args[0] if args else ""
                cwd = None
                i = 1
                while i < len(args):
                    if args[i] == "--cwd" and i + 1 < len(args):
                        cwd = args[i + 1]; i += 2
                    else:
                        i += 1
                proc = subprocess.Popen(
                    cmd_str, shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    cwd=cwd
                )
                json_success({
                    "action": "terminal_background",
                    "command": cmd_str,
                    "pid": proc.pid
                })
            else:
                json_error(f"Unknown terminal subcommand: {subcommand}")

        elif command == "accessibility":
            if subcommand == "check":
                accessibility_check()
            elif subcommand == "tree":
                pid = int(args[0]) if args and args[0] else None
                depth = int(args[1]) if len(args) > 1 else 3
                accessibility_tree(pid, depth)
            elif subcommand == "element-at":
                accessibility_element_at(int(args[0]), int(args[1]))
            elif subcommand == "click":
                role = args[0] if args else ""
                title = args[1] if len(args) > 1 else ""
                pid = int(args[2]) if len(args) > 2 and args[2] else None
                accessibility_click(role, title, pid)
            elif subcommand == "find":
                query = args[0] if args else ""
                accessibility_find(query)
            elif subcommand == "focused-position":
                focused_position()
            else:
                json_error(f"Unknown accessibility subcommand: {subcommand}")

        else:
            json_error(f"Unknown command: {command}")

    except Exception as e:
        json_error(str(e))

if __name__ == "__main__":
    main()

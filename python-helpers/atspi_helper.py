#!/usr/bin/env python3
"""
AT-SPI2 Accessibility Helper for Linux Control MCP.
Provides accessibility tree traversal, element finding, and interaction.
Requires: python3-atspi2 or pyatspi package.
"""

import sys
import json
import argparse

try:
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
    HAS_ATSPI = True
except (ImportError, ValueError):
    HAS_ATSPI = False

def json_output(data):
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0)

def json_error(msg):
    json_output({"success": False, "error": msg})

def json_success(data):
    data["success"] = True
    json_output(data)

def role_to_string(role):
    """Convert AT-SPI role enum to readable string."""
    try:
        return Atspi.Role(role).value_nick.replace("-", "_").upper()
    except:
        return f"UNKNOWN_{role}"

def build_tree(obj, depth=0, max_depth=3):
    """Recursively build accessibility tree from AT-SPI object."""
    if obj is None or depth > max_depth:
        return None

    try:
        role = role_to_string(obj.get_role())
        name = obj.get_name() or ""
        description = obj.get_description() or ""

        node = {
            "role": f"AX{role.title().replace('_', '')}",
            "title": name,
            "description": description,
        }

        # Get value if available
        try:
            value_iface = obj.get_value_iface()
            if value_iface:
                node["value"] = str(value_iface.get_current_value())
        except:
            pass

        # Try text interface
        try:
            text_iface = obj.get_text_iface()
            if text_iface:
                text_len = text_iface.get_character_count()
                if text_len > 0 and text_len < 1000:
                    node["value"] = text_iface.get_text(0, text_len)
        except:
            pass

        # Get position and size
        try:
            component = obj.get_component_iface()
            if component:
                rect = component.get_extents(Atspi.CoordType.SCREEN)
                node["position"] = {"x": rect.x, "y": rect.y}
                node["size"] = {"width": rect.width, "height": rect.height}
        except:
            pass

        # Get state
        try:
            states = obj.get_state_set()
            node["enabled"] = states.contains(Atspi.StateType.ENABLED)
            node["focused"] = states.contains(Atspi.StateType.FOCUSED)
            node["visible"] = states.contains(Atspi.StateType.VISIBLE)
        except:
            pass

        # Children
        if depth < max_depth:
            child_count = obj.get_child_count()
            if child_count > 0:
                children = []
                for i in range(min(child_count, 50)):  # Limit children
                    try:
                        child = obj.get_child_at_index(i)
                        child_node = build_tree(child, depth + 1, max_depth)
                        if child_node:
                            children.append(child_node)
                    except:
                        continue
                if children:
                    node["children"] = children
                node["childCount"] = child_count

        return node
    except Exception as e:
        return {"role": "AXUnknown", "error": str(e)}

def get_app_by_pid(pid):
    """Find AT-SPI application by PID."""
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        try:
            app = desktop.get_child_at_index(i)
            if app and app.get_process_id() == pid:
                return app
        except:
            continue
    return None

def get_active_app():
    """Get the currently focused application."""
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        try:
            app = desktop.get_child_at_index(i)
            if app:
                # Check if any window is focused
                for j in range(app.get_child_count()):
                    try:
                        win = app.get_child_at_index(j)
                        if win:
                            states = win.get_state_set()
                            if states.contains(Atspi.StateType.ACTIVE):
                                return app
                    except:
                        continue
        except:
            continue

    # Fallback: return first app
    if desktop.get_child_count() > 0:
        return desktop.get_child_at_index(0)
    return None

def cmd_tree(args):
    """Get accessibility tree."""
    if not HAS_ATSPI:
        json_error("AT-SPI2 not available. Install python3-gi and gir1.2-atspi-2.0")
        return

    if args.pid:
        app = get_app_by_pid(args.pid)
        if not app:
            json_error(f"No application found with PID {args.pid}")
            return
    else:
        app = get_active_app()
        if not app:
            json_error("No active application found")
            return

    tree = build_tree(app, 0, args.depth)
    json_success({
        "action": "accessibility_tree",
        "tree": tree,
        "app": app.get_name() or "Unknown",
        "pid": app.get_process_id(),
        "method": "atspi"
    })

def cmd_element_at(args):
    """Get element at screen coordinates."""
    if not HAS_ATSPI:
        json_error("AT-SPI2 not available")
        return

    desktop = Atspi.get_desktop(0)
    x, y = args.x, args.y

    # Search through all apps for element at position
    best_match = None
    best_area = float('inf')

    for i in range(desktop.get_child_count()):
        try:
            app = desktop.get_child_at_index(i)
            if not app:
                continue

            component = app.get_component_iface()
            if component:
                child = component.get_accessible_at_point(x, y, Atspi.CoordType.SCREEN)
                if child:
                    comp = child.get_component_iface()
                    if comp:
                        rect = comp.get_extents(Atspi.CoordType.SCREEN)
                        area = rect.width * rect.height
                        if area < best_area and area > 0:
                            best_area = area
                            best_match = child
        except:
            continue

    if best_match:
        node = build_tree(best_match, 0, 1)
        json_success({
            "action": "element_at",
            "x": x, "y": y,
            "element": node,
            "method": "atspi"
        })
    else:
        json_error(f"No element found at ({x}, {y})")

def find_elements(obj, role_filter, title_filter, depth=0, max_depth=10):
    """Recursively find elements matching criteria."""
    if obj is None or depth > max_depth:
        return []

    results = []

    try:
        role = role_to_string(obj.get_role())
        name = (obj.get_name() or "").lower()
        ax_role = f"AX{role.title().replace('_', '')}"

        role_match = not role_filter or role_filter.lower() in ax_role.lower()
        title_match = not title_filter or title_filter.lower() in name

        if role_match and title_match:
            results.append(obj)

        # Search children
        child_count = obj.get_child_count()
        for i in range(min(child_count, 100)):
            try:
                child = obj.get_child_at_index(i)
                results.extend(find_elements(child, role_filter, title_filter, depth + 1, max_depth))
            except:
                continue
    except:
        pass

    return results

def cmd_click(args):
    """Click element by role and title."""
    if not HAS_ATSPI:
        json_error("AT-SPI2 not available")
        return

    if args.pid:
        app = get_app_by_pid(args.pid)
    else:
        app = get_active_app()

    if not app:
        json_error("No application found")
        return

    matches = find_elements(app, args.role, args.title)

    if not matches:
        json_error(f"No element found matching role='{args.role}' title='{args.title}'")
        return

    element = matches[0]

    # Try action interface first
    try:
        action_iface = element.get_action_iface()
        if action_iface:
            for i in range(action_iface.get_n_actions()):
                action_name = action_iface.get_action_name(i)
                if action_name in ("click", "press", "activate"):
                    action_iface.do_action(i)
                    node = build_tree(element, 0, 0)
                    json_success({
                        "action": "accessibility_click",
                        "element": node,
                        "method": "action"
                    })
                    return
    except:
        pass

    # Fallback: get position and simulate click
    try:
        comp = element.get_component_iface()
        if comp:
            rect = comp.get_extents(Atspi.CoordType.SCREEN)
            cx = rect.x + rect.width // 2
            cy = rect.y + rect.height // 2
            import subprocess
            subprocess.run(["xdotool", "mousemove", "--sync", str(cx), str(cy)])
            subprocess.run(["xdotool", "click", "1"])
            json_success({
                "action": "accessibility_click",
                "element": build_tree(element, 0, 0),
                "method": "coordinate_click",
                "x": cx, "y": cy
            })
            return
    except:
        pass

    json_error("Could not click the element")

def cmd_focused_position(args):
    """Get position of currently focused element."""
    if not HAS_ATSPI:
        json_error("AT-SPI2 not available")
        return

    desktop = Atspi.get_desktop(0)

    for i in range(desktop.get_child_count()):
        try:
            app = desktop.get_child_at_index(i)
            if not app:
                continue

            # Find focused element recursively
            focused = _find_focused(app, 0)
            if focused:
                comp = focused.get_component_iface()
                if comp:
                    rect = comp.get_extents(Atspi.CoordType.SCREEN)

                    # Try to get caret position for text elements
                    source = "element"
                    cx, cy = rect.x + rect.width // 2, rect.y + rect.height // 2

                    try:
                        text_iface = focused.get_text_iface()
                        if text_iface:
                            offset = text_iface.get_caret_offset()
                            if offset >= 0:
                                char_rect = text_iface.get_character_extents(
                                    offset, Atspi.CoordType.SCREEN)
                                if char_rect.width > 0 or char_rect.height > 0:
                                    cx = char_rect.x + char_rect.width // 2
                                    cy = char_rect.y + char_rect.height // 2
                                    source = "caret"
                    except:
                        pass

                    json_success({
                        "action": "focused_position",
                        "source": source,
                        "x": cx, "y": cy,
                        "width": rect.width, "height": rect.height,
                        "app": app.get_name() or "Unknown"
                    })
                    return
        except:
            continue

    json_error("No focused element found")

def _find_focused(obj, depth):
    """Recursively find the focused element."""
    if obj is None or depth > 15:
        return None

    try:
        states = obj.get_state_set()
        if states.contains(Atspi.StateType.FOCUSED):
            return obj

        child_count = obj.get_child_count()
        for i in range(min(child_count, 50)):
            try:
                child = obj.get_child_at_index(i)
                result = _find_focused(child, depth + 1)
                if result:
                    return result
            except:
                continue
    except:
        pass

    return None

def main():
    parser = argparse.ArgumentParser(description="AT-SPI2 Accessibility Helper")
    subparsers = parser.add_subparsers(dest="command")

    # Tree
    tree_parser = subparsers.add_parser("tree")
    tree_parser.add_argument("--pid", type=int, default=None)
    tree_parser.add_argument("--depth", type=int, default=3)

    # Element at
    elem_parser = subparsers.add_parser("element_at")
    elem_parser.add_argument("x", type=int)
    elem_parser.add_argument("y", type=int)

    # Click
    click_parser = subparsers.add_parser("click")
    click_parser.add_argument("--role", default="")
    click_parser.add_argument("--title", default="")
    click_parser.add_argument("--pid", type=int, default=None)

    # Focused position
    subparsers.add_parser("focused_position")

    args = parser.parse_args()

    if args.command == "tree":
        cmd_tree(args)
    elif args.command == "element_at":
        cmd_element_at(args)
    elif args.command == "click":
        cmd_click(args)
    elif args.command == "focused_position":
        cmd_focused_position(args)
    else:
        json_error("Unknown command. Use: tree, element_at, click, focused_position")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Wayland Input Helper - Uses Mutter RemoteDesktop DBus API for input injection.
Works on GNOME Wayland where xdotool cannot inject input.
"""

import sys
import json
import time
import dbus

class WaylandInput:
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.session = None
        self.session_iface = None
        self._create_session()

    def _create_session(self):
        rd = self.bus.get_object(
            'org.gnome.Mutter.RemoteDesktop',
            '/org/gnome/Mutter/RemoteDesktop'
        )
        rd_iface = dbus.Interface(rd, 'org.gnome.Mutter.RemoteDesktop')
        session_path = rd_iface.CreateSession()
        self.session = self.bus.get_object(
            'org.gnome.Mutter.RemoteDesktop', session_path
        )
        self.session_iface = dbus.Interface(
            self.session, 'org.gnome.Mutter.RemoteDesktop.Session'
        )
        self.session_iface.Start()
        time.sleep(0.1)

    def stop(self):
        if self.session_iface:
            try:
                self.session_iface.Stop()
            except:
                pass

    def type_text(self, text):
        """Type text character by character using keysyms."""
        for c in text:
            keysym = ord(c)
            self.session_iface.NotifyKeyboardKeysym(
                dbus.UInt32(keysym), dbus.Boolean(True)
            )
            time.sleep(0.008)
            self.session_iface.NotifyKeyboardKeysym(
                dbus.UInt32(keysym), dbus.Boolean(False)
            )
            time.sleep(0.008)

    def press_key(self, keysym, modifiers=None):
        """Press a key with optional modifiers."""
        mod_keysyms = []
        if modifiers:
            mod_map = {
                'ctrl': 0xffe3,   # Control_L
                'shift': 0xffe1,  # Shift_L
                'alt': 0xffe9,    # Alt_L
                'super': 0xffeb,  # Super_L
            }
            for mod in modifiers:
                m = mod_map.get(mod.lower())
                if m:
                    mod_keysyms.append(m)

        # Press modifiers
        for m in mod_keysyms:
            self.session_iface.NotifyKeyboardKeysym(
                dbus.UInt32(m), dbus.Boolean(True)
            )
            time.sleep(0.01)

        # Press key
        self.session_iface.NotifyKeyboardKeysym(
            dbus.UInt32(keysym), dbus.Boolean(True)
        )
        time.sleep(0.02)
        self.session_iface.NotifyKeyboardKeysym(
            dbus.UInt32(keysym), dbus.Boolean(False)
        )
        time.sleep(0.01)

        # Release modifiers (reverse order)
        for m in reversed(mod_keysyms):
            self.session_iface.NotifyKeyboardKeysym(
                dbus.UInt32(m), dbus.Boolean(False)
            )
            time.sleep(0.01)

    def click(self, button='left'):
        """Click mouse button at current position."""
        btn_map = {'left': 272, 'right': 273, 'middle': 274}
        btn = btn_map.get(button, 272)
        self.session_iface.NotifyPointerButton(
            dbus.Int32(btn), dbus.Boolean(True)
        )
        time.sleep(0.05)
        self.session_iface.NotifyPointerButton(
            dbus.Int32(btn), dbus.Boolean(False)
        )

    def move_relative(self, dx, dy):
        """Move mouse by relative amount."""
        self.session_iface.NotifyPointerMotion(
            dbus.Double(dx), dbus.Double(dy)
        )

    def scroll(self, dx=0, dy=0):
        """Scroll by amount. Positive dy = down."""
        if dy != 0:
            self.session_iface.NotifyPointerAxisDiscrete(
                dbus.UInt32(0),  # vertical axis
                dbus.Int32(1 if dy > 0 else -1)
            )
        if dx != 0:
            self.session_iface.NotifyPointerAxisDiscrete(
                dbus.UInt32(1),  # horizontal axis
                dbus.Int32(1 if dx > 0 else -1)
            )


# Key name to X11 keysym mapping
KEY_MAP = {
    'return': 0xff0d, 'enter': 0xff0d,
    'tab': 0xff09,
    'escape': 0xff1b, 'esc': 0xff1b,
    'backspace': 0xff08,
    'delete': 0xffff,
    'space': 0x0020,
    'up': 0xff52, 'down': 0xff54, 'left': 0xff51, 'right': 0xff53,
    'home': 0xff50, 'end': 0xff57,
    'page_up': 0xff55, 'pageup': 0xff55,
    'page_down': 0xff56, 'pagedown': 0xff56,
    'insert': 0xff63,
    'f1': 0xffbe, 'f2': 0xffbf, 'f3': 0xffc0, 'f4': 0xffc1,
    'f5': 0xffc2, 'f6': 0xffc3, 'f7': 0xffc4, 'f8': 0xffc5,
    'f9': 0xffc6, 'f10': 0xffc7, 'f11': 0xffc8, 'f12': 0xffc9,
    'a': 0x61, 'b': 0x62, 'c': 0x63, 'd': 0x64, 'e': 0x65,
    'f': 0x66, 'g': 0x67, 'h': 0x68, 'i': 0x69, 'j': 0x6a,
    'k': 0x6b, 'l': 0x6c, 'm': 0x6d, 'n': 0x6e, 'o': 0x6f,
    'p': 0x70, 'q': 0x71, 'r': 0x72, 's': 0x73, 't': 0x74,
    'u': 0x75, 'v': 0x76, 'w': 0x77, 'x': 0x78, 'y': 0x79, 'z': 0x7a,
}


def json_output(data):
    print(json.dumps(data, ensure_ascii=False))

def json_success(data):
    data["success"] = True
    json_output(data)

def json_error(msg):
    json_output({"success": False, "error": msg})


def main():
    if len(sys.argv) < 2:
        json_error("Usage: wayland_input.py <type|press|click|move|scroll> [args]")
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    try:
        wi = WaylandInput()

        if command == "type":
            text = args[0] if args else ""
            wi.type_text(text)
            json_success({"action": "keyboard_type", "text": text, "length": len(text)})

        elif command == "press":
            key_name = args[0].lower() if args else ""
            mods = args[1].split(",") if len(args) > 1 and args[1] else []
            keysym = KEY_MAP.get(key_name, ord(key_name[0]) if key_name else 0)
            wi.press_key(keysym, mods)
            json_success({"action": "keyboard_press", "key": key_name, "modifiers": mods})

        elif command == "hotkey":
            combo = args[0] if args else ""
            parts = combo.lower().split("+")
            key = parts[-1]
            mods = parts[:-1]
            keysym = KEY_MAP.get(key, ord(key[0]) if key else 0)
            wi.press_key(keysym, mods)
            json_success({"action": "keyboard_press", "key": key, "modifiers": mods})

        elif command == "click":
            button = args[0] if args else "left"
            wi.click(button)
            json_success({"action": "mouse_click", "button": button})

        elif command == "move":
            dx = float(args[0]) if args else 0
            dy = float(args[1]) if len(args) > 1 else 0
            wi.move_relative(dx, dy)
            json_success({"action": "mouse_move_relative", "dx": dx, "dy": dy})

        elif command == "scroll":
            dy = int(args[0]) if args else 0
            dx = int(args[1]) if len(args) > 1 else 0
            for _ in range(abs(dy)):
                wi.scroll(dy=dy)
                time.sleep(0.05)
            json_success({"action": "mouse_scroll", "deltaY": dy, "deltaX": dx})

        else:
            json_error(f"Unknown command: {command}")

        wi.stop()

    except Exception as e:
        json_error(str(e))


if __name__ == "__main__":
    main()

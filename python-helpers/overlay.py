#!/usr/bin/env python3
"""
Linux Overlay Animation System - GTK3/Cairo-based visual feedback overlay.
Provides click ripples, trails, typing indicators, highlights, and scroll animations
via stdin JSON commands. Fullscreen transparent, click-through window at 60 FPS.
"""

import sys
import os
import json
import math
import time
import signal
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any

# Ensure DISPLAY is set for X11
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, cairo as Cairo
import cairo as _pycairo


class ClickStyle(Enum):
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"


@dataclass
class Color:
    r: float
    g: float
    b: float
    a: float = 1.0

    @staticmethod
    def from_hex(hex_color: str, alpha: float = 1.0) -> 'Color':
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return Color(r, g, b, alpha)
        return Color(0.0, 0.47, 1.0, alpha)  # Default blue


@dataclass
class Animation:
    start_time: float
    duration: float

    def progress(self, current_time: float) -> float:
        elapsed = current_time - self.start_time
        return max(0.0, min(1.0, elapsed / self.duration))

    def is_complete(self, current_time: float) -> bool:
        return self.progress(current_time) >= 1.0


@dataclass
class ClickAnimation(Animation):
    x: float = 0.0
    y: float = 0.0
    color: Color = field(default_factory=lambda: Color(0.0, 0.47, 1.0))
    style: ClickStyle = ClickStyle.LEFT
    max_radius: float = 100.0


@dataclass
class TrailAnimation(Animation):
    points: List[Tuple[float, float]] = field(default_factory=list)
    color: Color = field(default_factory=lambda: Color(0.2, 0.78, 0.35))
    width: float = 2.0


@dataclass
class TypeAnimation(Animation):
    x: float = 0.0
    y: float = 0.0
    text: str = ""
    color: Color = field(default_factory=lambda: Color(0.69, 0.32, 0.87))

    def get_revealed_text(self, current_time: float) -> Tuple[str, bool]:
        progress = self.progress(current_time)
        if len(self.text) == 0:
            return "", False
        max_chars = len(self.text)
        char_progress = progress * max_chars
        revealed_count = min(int(math.ceil(char_progress)), max_chars)
        cursor_visible = (int(current_time * 4) % 2) == 0
        return self.text[:revealed_count], cursor_visible


@dataclass
class HighlightAnimation(Animation):
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 50.0
    color: Color = field(default_factory=lambda: Color(1.0, 0.58, 0.0))
    label: Optional[str] = None
    corner_length: float = 15.0

    def get_pulse_scale(self, current_time: float) -> float:
        progress = self.progress(current_time)
        angle = progress * 2 * math.pi
        return 1.5 + math.sin(angle) * 0.5


@dataclass
class ScrollAnimation(Animation):
    x: float = 0.0
    y: float = 0.0
    direction: str = "down"
    color: Color = field(default_factory=lambda: Color(0.0, 0.78, 0.75))
    chevron_size: float = 15.0


class OverlayWindow(Gtk.Window):
    """Fullscreen transparent GTK3 overlay for animations."""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_title("Overlay Animation System")
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

        # Transparent visual
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Fullscreen
        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0) if display else None
        if monitor:
            monitor_geom = monitor.get_geometry()
        else:
            monitor_geom = screen.get_monitor_geometry(0)
        self.move(monitor_geom.x, monitor_geom.y)
        self.resize(monitor_geom.width, monitor_geom.height)

        # Click-through using cairo region
        self.connect('realize', self._on_realize)
        self.connect('draw', self.on_draw)
        self.connect('destroy', self.on_destroy)

        # Animation state
        self.animations: Dict[str, List[Animation]] = defaultdict(list)
        self.last_input_time = time.time()
        self.running = True

        # Setup stdin watch
        self._setup_stdin_watch()

        # 60 FPS refresh
        GLib.timeout_add(17, self._tick)

        # 120s idle timeout
        GLib.timeout_add_seconds(120, self._check_idle_timeout)

    def _on_realize(self, widget):
        """Set input shape to make window click-through after realized."""
        try:
            window = self.get_window()
            if window:
                # GTK 3.18+ pass-through mode
                if hasattr(window, 'set_pass_through'):
                    window.set_pass_through(True)
                else:
                    # Fallback: use subprocess to set empty input region via xdotool
                    import subprocess
                    xid = window.get_xid()
                    subprocess.run(
                        ['xprop', '-id', str(xid), '-format', '_NET_WM_STATE', '32a',
                         '-set', '_NET_WM_STATE', '_NET_WM_STATE_SKIP_TASKBAR'],
                        capture_output=True
                    )
        except Exception as e:
            print(f"[overlay] Click-through setup failed: {e}", file=sys.stderr)

    def _setup_stdin_watch(self):
        """Register stdin for non-blocking command reading."""
        self.stdin_handler_id = GLib.io_add_watch(
            sys.stdin.fileno(),
            GLib.IOCondition.IN | GLib.IOCondition.HUP,
            self._on_stdin_ready
        )

    def _on_stdin_ready(self, fd, condition):
        """Handle incoming JSON command from stdin."""
        if condition & GLib.IOCondition.HUP:
            self.quit()
            return False
        try:
            line = sys.stdin.readline()
            if not line:
                self.quit()
                return False
            line = line.strip()
            if not line:
                return True
            command = json.loads(line)
            self._process_command(command)
            self.last_input_time = time.time()
        except json.JSONDecodeError as e:
            print(f"[overlay] JSON decode error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[overlay] Command error: {e}", file=sys.stderr)
        return True

    def _process_command(self, cmd: Dict[str, Any]):
        """Parse and execute animation command.

        Expected format from overlay-bridge.ts:
        {"action": "click", "x": 100, "y": 200, "options": {"button": "left", "color": "#007AFF", "duration": 0.5}}
        {"action": "trail", "points": [...], "options": {"color": "#34C759", "duration": 1.5}}
        {"action": "type", "x": 100, "y": 200, "text": "hello", "options": {"color": "#AF52DE"}}
        {"action": "highlight", "x": 100, "y": 200, "width": 300, "height": 50, "options": {...}}
        {"action": "scroll", "x": 100, "y": 200, "direction": "down", "options": {...}}
        """
        action = cmd.get('action', '').lower()

        if action in ('quit', 'exit'):
            self.quit()
            return

        try:
            current_time = time.time()
            opts = cmd.get('options', {})

            if action == 'click':
                self._handle_click(cmd, opts, current_time)
            elif action == 'trail':
                self._handle_trail(cmd, opts, current_time)
            elif action == 'type':
                self._handle_type(cmd, opts, current_time)
            elif action == 'highlight':
                self._handle_highlight(cmd, opts, current_time)
            elif action == 'scroll':
                self._handle_scroll(cmd, opts, current_time)
            else:
                print(f"[overlay] Unknown action: {action}", file=sys.stderr)
        except Exception as e:
            print(f"[overlay] Error processing {action}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)

    def _handle_click(self, cmd: Dict, opts: Dict, current_time: float):
        x = float(cmd.get('x', 0))
        y = float(cmd.get('y', 0))
        color = Color.from_hex(opts.get('color', '#007AFF'))
        duration = float(opts.get('duration', 0.6))
        button = opts.get('button', 'left').lower()

        try:
            style = ClickStyle(button)
        except ValueError:
            style = ClickStyle.LEFT

        anim = ClickAnimation(
            start_time=current_time,
            duration=duration,
            x=x, y=y,
            color=color,
            style=style
        )
        self.animations['click'].append(anim)

    def _handle_trail(self, cmd: Dict, opts: Dict, current_time: float):
        raw_points = cmd.get('points', [])
        points = []
        for p in raw_points:
            if isinstance(p, dict):
                points.append((float(p.get('x', 0)), float(p.get('y', 0))))
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                points.append((float(p[0]), float(p[1])))

        if len(points) < 2:
            return

        color = Color.from_hex(opts.get('color', '#34C759'))
        width = float(opts.get('width', 2.0))
        duration = float(opts.get('duration', 0.4))

        anim = TrailAnimation(
            start_time=current_time,
            duration=duration,
            points=points,
            color=color,
            width=width
        )
        self.animations['trail'].append(anim)

    def _handle_type(self, cmd: Dict, opts: Dict, current_time: float):
        x = float(cmd.get('x', 0))
        y = float(cmd.get('y', 0))
        text = str(cmd.get('text', ''))
        color = Color.from_hex(opts.get('color', '#AF52DE'))
        duration = float(opts.get('duration', 1.5))

        anim = TypeAnimation(
            start_time=current_time,
            duration=duration,
            x=x, y=y,
            text=text,
            color=color
        )
        self.animations['type'].append(anim)

    def _handle_highlight(self, cmd: Dict, opts: Dict, current_time: float):
        x = float(cmd.get('x', 0))
        y = float(cmd.get('y', 0))
        width = float(cmd.get('width', 100))
        height = float(cmd.get('height', 50))
        color = Color.from_hex(opts.get('color', '#FF9500'))
        label = opts.get('label')
        duration = float(opts.get('duration', 2.0))

        anim = HighlightAnimation(
            start_time=current_time,
            duration=duration,
            x=x, y=y,
            width=width, height=height,
            color=color,
            label=label
        )
        self.animations['highlight'].append(anim)

    def _handle_scroll(self, cmd: Dict, opts: Dict, current_time: float):
        x = float(cmd.get('x', 0))
        y = float(cmd.get('y', 0))
        direction = str(cmd.get('direction', opts.get('direction', 'down'))).lower()
        color = Color.from_hex(opts.get('color', '#00C7BE'))
        duration = float(opts.get('duration', 0.8))

        anim = ScrollAnimation(
            start_time=current_time,
            duration=duration,
            x=x, y=y,
            direction=direction,
            color=color
        )
        self.animations['scroll'].append(anim)

    def on_draw(self, widget, ctx):
        """Render all active animations."""
        # Clear with transparent background
        ctx.set_operator(0)  # CLEAR
        ctx.paint()
        ctx.set_operator(2)  # OVER

        current_time = time.time()
        self._render_animations(ctx, current_time)
        self._cleanup_animations(current_time)
        return False

    def _render_animations(self, ctx, current_time: float):
        for click_anim in self.animations['click']:
            if not click_anim.is_complete(current_time):
                self._draw_click(ctx, click_anim, current_time)

        for trail_anim in self.animations['trail']:
            if not trail_anim.is_complete(current_time):
                self._draw_trail(ctx, trail_anim, current_time)

        for type_anim in self.animations['type']:
            if not type_anim.is_complete(current_time):
                self._draw_type(ctx, type_anim, current_time)

        for highlight_anim in self.animations['highlight']:
            if not highlight_anim.is_complete(current_time):
                self._draw_highlight(ctx, highlight_anim, current_time)

        for scroll_anim in self.animations['scroll']:
            if not scroll_anim.is_complete(current_time):
                self._draw_scroll(ctx, scroll_anim, current_time)

    def _draw_click(self, ctx, anim: ClickAnimation, current_time: float):
        progress = anim.progress(current_time)
        rings = 3 if anim.style == ClickStyle.DOUBLE else 2

        ctx.save()
        ctx.translate(anim.x, anim.y)

        for ring_idx in range(rings):
            ring_progress = progress + (ring_idx * 0.15)
            if ring_progress > 1.0:
                continue
            radius = anim.max_radius * ring_progress
            fade = 1.0 - ring_progress
            alpha = fade * anim.color.a
            ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, alpha)
            ctx.set_line_width(2.0)
            ctx.arc(0, 0, radius, 0, 2 * math.pi)
            ctx.stroke()

        ctx.restore()

    def _draw_trail(self, ctx, anim: TrailAnimation, current_time: float):
        progress = anim.progress(current_time)
        if len(anim.points) < 2:
            return

        total = len(anim.points)
        visible_count = int(math.ceil(total * progress))

        ctx.save()
        ctx.set_line_width(anim.width)
        ctx.set_line_cap(1)  # ROUND
        ctx.set_line_join(1)  # ROUND

        for i in range(min(visible_count, total) - 1):
            p1 = anim.points[i]
            p2 = anim.points[i + 1]
            seg_alpha = (1.0 - (i / max(total - 1, 1)) * 0.5) * (1.0 - progress * 0.3)
            alpha = seg_alpha * anim.color.a
            ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, alpha)
            ctx.move_to(p1[0], p1[1])
            ctx.line_to(p2[0], p2[1])
            ctx.stroke()

        # Leading glow dot
        if visible_count > 0 and visible_count <= total:
            last = anim.points[min(visible_count - 1, total - 1)]
            ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, progress * anim.color.a)
            ctx.arc(last[0], last[1], anim.width * 3, 0, 2 * math.pi)
            ctx.fill()

        ctx.restore()

    def _draw_type(self, ctx, anim: TypeAnimation, current_time: float):
        revealed_text, cursor_visible = anim.get_revealed_text(current_time)
        if not revealed_text and not cursor_visible:
            return

        progress = anim.progress(current_time)
        alpha = min(1.0, progress * 2) * anim.color.a

        ctx.save()
        ctx.translate(anim.x, anim.y)

        font_size = 16
        padding = 8
        text_height = font_size
        text_width = len(revealed_text) * font_size * 0.6 + 10

        # Background pill
        ctx.set_source_rgba(0, 0, 0, alpha * 0.1)
        self._draw_rounded_rect(ctx, -padding, -text_height / 2 - padding,
                                text_width + 2 * padding, text_height + 2 * padding, 6)
        ctx.fill()

        # Text
        ctx.set_font_size(font_size)
        ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, alpha)
        ctx.move_to(0, 0)
        ctx.show_text(revealed_text)

        # Cursor
        if cursor_visible and revealed_text:
            extents = ctx.text_extents(revealed_text)
            ctx.move_to(extents.width, -text_height / 4)
            ctx.line_to(extents.width, text_height / 4)
            ctx.stroke()

        ctx.restore()

    def _draw_highlight(self, ctx, anim: HighlightAnimation, current_time: float):
        progress = anim.progress(current_time)
        pulse = anim.get_pulse_scale(current_time)
        border_width = 2.0 * pulse
        alpha = (1.0 - progress) * anim.color.a

        ctx.save()
        ctx.set_line_width(border_width)
        ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, alpha)

        ctx.rectangle(anim.x, anim.y, anim.width, anim.height)
        ctx.stroke()

        # Corner brackets
        cl = anim.corner_length
        corners = [
            (anim.x, anim.y, [(cl, 0), (0, 0), (0, cl)]),
            (anim.x + anim.width, anim.y, [(-cl, 0), (0, 0), (0, cl)]),
            (anim.x, anim.y + anim.height, [(cl, 0), (0, 0), (0, -cl)]),
            (anim.x + anim.width, anim.y + anim.height, [(-cl, 0), (0, 0), (0, -cl)]),
        ]
        for cx, cy, path in corners:
            for i, (dx, dy) in enumerate(path):
                if i == 0:
                    ctx.move_to(cx + dx, cy + dy)
                else:
                    ctx.line_to(cx + dx, cy + dy)
            ctx.stroke()

        if anim.label:
            ctx.set_font_size(12)
            extents = ctx.text_extents(anim.label)
            label_x = anim.x + anim.width / 2 - extents.width / 2
            label_y = anim.y - 8
            ctx.move_to(label_x, label_y)
            ctx.show_text(anim.label)

        ctx.restore()

    def _draw_scroll(self, ctx, anim: ScrollAnimation, current_time: float):
        progress = anim.progress(current_time)
        alpha = (1.0 - progress) * anim.color.a

        ctx.save()
        ctx.translate(anim.x, anim.y)
        ctx.set_line_width(2.0)
        ctx.set_line_cap(1)  # ROUND
        ctx.set_line_join(1)  # ROUND

        cs = anim.chevron_size
        spacing = cs * 0.6
        y_dir = 1 if anim.direction == 'down' else -1

        for ci in range(3):
            cascade_delay = ci * 0.1
            cp = max(0, min(1.0, (progress - cascade_delay) / 0.3))
            ca = cp * (1.0 - progress) * alpha
            ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, ca)

            yo = ci * spacing * y_dir
            if anim.direction == 'down':
                ctx.move_to(-cs / 2, yo)
                ctx.line_to(0, yo + cs)
                ctx.line_to(cs / 2, yo)
            else:
                ctx.move_to(-cs / 2, yo + cs)
                ctx.line_to(0, yo)
                ctx.line_to(cs / 2, yo + cs)
            ctx.stroke()

        ctx.restore()

    def _draw_rounded_rect(self, ctx, x, y, width, height, radius):
        ctx.new_path()
        ctx.move_to(x + radius, y)
        ctx.line_to(x + width - radius, y)
        ctx.curve_to(x + width, y, x + width, y + radius, x + width, y + radius)
        ctx.line_to(x + width, y + height - radius)
        ctx.curve_to(x + width, y + height, x + width - radius, y + height, x + width - radius, y + height)
        ctx.line_to(x + radius, y + height)
        ctx.curve_to(x, y + height, x, y + height - radius, x, y + height - radius)
        ctx.line_to(x, y + radius)
        ctx.curve_to(x, y, x + radius, y, x + radius, y)
        ctx.close_path()

    def _cleanup_animations(self, current_time: float):
        for anim_type in self.animations:
            self.animations[anim_type] = [
                a for a in self.animations[anim_type]
                if not a.is_complete(current_time)
            ]

    def _tick(self) -> bool:
        if self.running:
            self.queue_draw()
        return self.running

    def _check_idle_timeout(self) -> bool:
        if time.time() - self.last_input_time > 120:
            print("[overlay] Idle timeout (120s) - exiting", file=sys.stderr)
            self.quit()
            return False
        return True

    def on_destroy(self, widget):
        self.running = False
        if hasattr(self, 'stdin_handler_id') and self.stdin_handler_id:
            GLib.source_remove(self.stdin_handler_id)
        Gtk.main_quit()

    def quit(self):
        self.running = False
        Gtk.main_quit()


def main():
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

    window = OverlayWindow()
    window.show_all()

    # Signal READY to the bridge
    print("READY", flush=True)

    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Linux Overlay Animation System - GTK3/Cairo-based visual feedback overlay.
Provides click ripples, trails, typing indicators, highlights, and scroll animations
via stdin JSON commands. Fullscreen transparent, click-through window at 60 FPS.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

import sys
import json
import math
import time
import signal
import threading
from gi.repository import Gtk, Gdk, GLib, Cairo
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any


class ClickStyle(Enum):
    """Click button style variants."""
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"


@dataclass
class Color:
    """RGBA color representation."""
    r: float
    g: float
    b: float
    a: float = 1.0

    @staticmethod
    def from_hex(hex_color: str, alpha: float = 1.0) -> 'Color':
        """Parse hex color string (#RRGGBB) to Color."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16) / 255.0, int(hex_color[2:4], 16) / 255.0, int(hex_color[4:6], 16) / 255.0
            return Color(r, g, b, alpha)
        raise ValueError(f"Invalid hex color: {hex_color}")


@dataclass
class Animation:
    """Base animation state."""
    start_time: float
    duration: float

    def progress(self, current_time: float) -> float:
        """Get animation progress [0.0, 1.0], clamps to [0.0, 1.0]."""
        elapsed = current_time - self.start_time
        return max(0.0, min(1.0, elapsed / self.duration))

    def is_complete(self, current_time: float) -> bool:
        """Check if animation has finished."""
        return self.progress(current_time) >= 1.0


@dataclass
class ClickAnimation(Animation):
    """Expanding circle ripple animation."""
    x: float
    y: float
    color: Color
    style: ClickStyle
    max_radius: float = 100.0


@dataclass
class TrailAnimation(Animation):
    """Mouse trail with fading segments."""
    points: List[Tuple[float, float]]
    color: Color
    width: float
    segments: List[Dict[str, Any]] = None  # Computed segments with fade

    def __post_init__(self):
        if self.segments is None:
            self._compute_segments()

    def _compute_segments(self):
        """Precompute trail segments with fade parameters."""
        self.segments = []
        if len(self.points) < 2:
            return
        for i in range(len(self.points) - 1):
            self.segments.append({
                'p1': self.points[i],
                'p2': self.points[i + 1],
                'base_alpha': 1.0 - (i / (len(self.points) - 1)) * 0.5,  # 1.0 to 0.5 gradient
            })
        # Leading glow dot
        self.segments.append({
            'glow': self.points[-1],
            'base_alpha': 1.0,
        })


@dataclass
class TypeAnimation(Animation):
    """Typing indicator with character reveal."""
    x: float
    y: float
    text: str
    color: Color
    char_index: int = 0  # Current revealed character count

    def get_revealed_text(self, current_time: float) -> Tuple[str, bool]:
        """Get text revealed so far and whether cursor should blink."""
        progress = self.progress(current_time)
        if len(self.text) == 0:
            return "", False
        # Distribute characters across animation duration
        max_chars = len(self.text)
        char_progress = progress * max_chars
        revealed_count = min(int(math.ceil(char_progress)), max_chars)
        cursor_visible = (int(current_time * 4) % 2) == 0  # Blink at ~2Hz
        return self.text[:revealed_count], cursor_visible


@dataclass
class HighlightAnimation(Animation):
    """Pulsing rectangle highlight with label."""
    x: float
    y: float
    width: float
    height: float
    color: Color
    label: Optional[str] = None
    corner_length: float = 15.0

    def get_pulse_scale(self, current_time: float) -> float:
        """Get border width pulse via sine wave."""
        progress = self.progress(current_time)
        angle = progress * 2 * math.pi
        return 1.5 + math.sin(angle) * 0.5


@dataclass
class ScrollAnimation(Animation):
    """Scroll direction indicator with staggered chevrons."""
    x: float
    y: float
    direction: str  # "up" or "down"
    color: Color
    chevron_size: float = 15.0


class OverlayWindow(Gtk.Window):
    """Fullscreen transparent GTK3 overlay for animations."""

    def __init__(self):
        super().__init__(Gtk.WindowType.POPUP)
        self.set_title("Overlay Animation System")
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

        # Make window fullscreen and transparent
        screen = self.get_screen()
        if screen.get_rgba_visual():
            self.set_visual(screen.get_rgba_visual())

        # Set to cover entire screen
        monitor_geom = screen.get_monitor_geometry(0)
        self.move(monitor_geom.x, monitor_geom.y)
        self.resize(screen.get_width(), screen.get_height())
        self.fullscreen()

        # Click-through: set empty input region via input mask
        self.set_input_shape_region(Gdk.Region.new())

        # Connect signals
        self.connect('draw', self.on_draw)
        self.connect('destroy', self.on_destroy)

        # Animation state
        self.animations: Dict[str, List[Animation]] = defaultdict(list)
        self.last_input_time = time.time()
        self.running = True
        self.stdin_handler_id = None

        # Setup stdin watch for JSON commands
        self._setup_stdin_watch()

        # 60 FPS refresh timer (16.67ms)
        GLib.timeout_add(17, self._tick)

        # 120s idle timeout
        GLib.timeout_add_seconds(120, self._check_idle_timeout)

    def _setup_stdin_watch(self):
        """Register stdin for non-blocking command reading."""
        stdin_fileno = sys.stdin.fileno()
        self.stdin_handler_id = GLib.io_add_watch(
            stdin_fileno,
            GLib.IOCondition.IN,
            self._on_stdin_ready
        )

    def _on_stdin_ready(self, fd, condition):
        """Handle incoming JSON command from stdin."""
        try:
            line = sys.stdin.readline()
            if not line:
                # EOF - graceful shutdown
                self.quit()
                return False
            command = json.loads(line.strip())
            self._process_command(command)
            self.last_input_time = time.time()
        except json.JSONDecodeError as e:
            print(f"[overlay] JSON decode error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[overlay] Command error: {e}", file=sys.stderr)
        return True  # Keep watching

    def _process_command(self, cmd: Dict[str, Any]):
        """Parse and execute animation command."""
        action = cmd.get('action', '').lower()

        if action in ('quit', 'exit'):
            self.quit()
            return

        try:
            current_time = time.time()

            if action == 'click':
                self._handle_click(cmd.get('click', {}), current_time)
            elif action == 'trail':
                self._handle_trail(cmd.get('trail', {}), current_time)
            elif action == 'type':
                self._handle_type(cmd.get('type_anim', {}), current_time)
            elif action == 'highlight':
                self._handle_highlight(cmd.get('highlight', {}), current_time)
            elif action == 'scroll':
                self._handle_scroll(cmd.get('scroll', {}), current_time)
        except Exception as e:
            print(f"[overlay] Error processing {action}: {e}", file=sys.stderr)

    def _handle_click(self, params: Dict, current_time: float):
        """Create click ripple animation."""
        x = float(params.get('x', 0))
        y = float(params.get('y', 0))
        color = Color.from_hex(params.get('color', '#007AFF'))
        duration = float(params.get('duration', 0.6))
        button = params.get('button', 'left').lower()

        try:
            style = ClickStyle(button)
        except ValueError:
            style = ClickStyle.LEFT

        anim = ClickAnimation(
            start_time=current_time,
            duration=duration,
            x=x,
            y=y,
            color=color,
            style=style
        )
        self.animations['click'].append(anim)

    def _handle_trail(self, params: Dict, current_time: float):
        """Create mouse trail animation."""
        points = [tuple(p) for p in params.get('points', [])]
        if len(points) < 2:
            return
        color = Color.from_hex(params.get('color', '#34C759'))
        width = float(params.get('width', 2.0))
        duration = float(params.get('duration', 0.4))

        anim = TrailAnimation(
            start_time=current_time,
            duration=duration,
            points=points,
            color=color,
            width=width
        )
        self.animations['trail'].append(anim)

    def _handle_type(self, params: Dict, current_time: float):
        """Create typing indicator animation."""
        x = float(params.get('x', 0))
        y = float(params.get('y', 0))
        text = str(params.get('text', ''))
        color = Color.from_hex(params.get('color', '#AF52DE'))
        duration = float(params.get('duration', 1.5))

        anim = TypeAnimation(
            start_time=current_time,
            duration=duration,
            x=x,
            y=y,
            text=text,
            color=color
        )
        self.animations['type'].append(anim)

    def _handle_highlight(self, params: Dict, current_time: float):
        """Create highlight animation."""
        x = float(params.get('x', 0))
        y = float(params.get('y', 0))
        width = float(params.get('width', 100))
        height = float(params.get('height', 50))
        color = Color.from_hex(params.get('color', '#FF9500'))
        label = params.get('label')
        duration = float(params.get('duration', 2.0))

        anim = HighlightAnimation(
            start_time=current_time,
            duration=duration,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
            label=label
        )
        self.animations['highlight'].append(anim)

    def _handle_scroll(self, params: Dict, current_time: float):
        """Create scroll indicator animation."""
        x = float(params.get('x', 0))
        y = float(params.get('y', 0))
        direction = str(params.get('direction', 'down')).lower()
        color = Color.from_hex(params.get('color', '#00C7BE'))
        duration = float(params.get('duration', 0.8))

        anim = ScrollAnimation(
            start_time=current_time,
            duration=duration,
            x=x,
            y=y,
            direction=direction,
            color=color
        )
        self.animations['scroll'].append(anim)

    def on_draw(self, widget, ctx: Cairo.Context):
        """Render all active animations."""
        # Clear with transparent background
        ctx.set_operator(Cairo.Operator.CLEAR)
        ctx.paint()
        ctx.set_operator(Cairo.Operator.OVER)

        current_time = time.time()
        self._render_animations(ctx, current_time)

        # Clean up expired animations
        self._cleanup_animations(current_time)

        return False

    def _render_animations(self, ctx: Cairo.Context, current_time: float):
        """Draw all active animations."""
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

    def _draw_click(self, ctx: Cairo.Context, anim: ClickAnimation, current_time: float):
        """Draw expanding circle ripple with style variants."""
        progress = anim.progress(current_time)

        # Multi-ring effect based on style
        if anim.style == ClickStyle.DOUBLE:
            rings = 3
        else:
            rings = 2

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
            ctx.arc(0, 0, radius, 0, 2 * math.pi)
            ctx.stroke()

        ctx.restore()

    def _draw_trail(self, ctx: Cairo.Context, anim: TrailAnimation, current_time: float):
        """Draw mouse trail with fading segments and leading glow."""
        progress = anim.progress(current_time)
        visible_segments = int(math.ceil(len(anim.segments) * progress))

        ctx.save()
        ctx.set_line_width(anim.width)
        ctx.set_line_cap(Cairo.LineCap.ROUND)
        ctx.set_line_join(Cairo.LineJoin.ROUND)

        # Draw segments
        for segment in anim.segments[:visible_segments]:
            if 'glow' in segment:
                # Leading glow dot
                glow_pos = segment['glow']
                glow_alpha = segment['base_alpha'] * progress * anim.color.a
                ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, glow_alpha)
                ctx.arc(glow_pos[0], glow_pos[1], anim.width * 3, 0, 2 * math.pi)
                ctx.fill()
            else:
                # Line segment
                p1, p2 = segment['p1'], segment['p2']
                fade = segment['base_alpha'] * (1.0 - progress * 0.3)
                alpha = fade * anim.color.a
                ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, alpha)
                ctx.move_to(p1[0], p1[1])
                ctx.line_to(p2[0], p2[1])
                ctx.stroke()

        ctx.restore()

    def _draw_type(self, ctx: Cairo.Context, anim: TypeAnimation, current_time: float):
        """Draw typing indicator with character reveal and cursor."""
        revealed_text, cursor_visible = anim.get_revealed_text(current_time)
        if not revealed_text and not cursor_visible:
            return

        progress = anim.progress(current_time)
        alpha = min(1.0, progress * 2) * anim.color.a

        ctx.save()
        ctx.translate(anim.x, anim.y)

        # Rounded pill background
        font_size = 16
        padding = 8
        text_height = font_size
        text_width = len(revealed_text) * font_size * 0.6 + 10  # Rough estimate

        ctx.set_source_rgba(0, 0, 0, alpha * 0.1)
        self._draw_rounded_rect(ctx, -padding, -text_height/2 - padding,
                               text_width + 2*padding, text_height + 2*padding, 6)
        ctx.fill()

        # Text
        ctx.set_font_size(font_size)
        ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, alpha)
        ctx.move_to(0, 0)
        ctx.show_text(revealed_text)

        # Blinking cursor
        if cursor_visible and revealed_text:
            extents = ctx.text_extents(revealed_text)
            ctx.move_to(extents.width, -text_height/4)
            ctx.line_to(extents.width, text_height/4)
            ctx.stroke()

        ctx.restore()

    def _draw_highlight(self, ctx: Cairo.Context, anim: HighlightAnimation, current_time: float):
        """Draw pulsing rectangle highlight with corner brackets and label."""
        progress = anim.progress(current_time)
        pulse = anim.get_pulse_scale(current_time)
        border_width = 2.0 * pulse
        alpha = (1.0 - progress) * anim.color.a

        ctx.save()
        ctx.set_line_width(border_width)
        ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, alpha)

        # Main rectangle
        ctx.rectangle(anim.x, anim.y, anim.width, anim.height)
        ctx.stroke()

        # Corner brackets
        corner_len = anim.corner_length
        corners = [
            (anim.x, anim.y),  # Top-left
            (anim.x + anim.width, anim.y),  # Top-right
            (anim.x, anim.y + anim.height),  # Bottom-left
            (anim.x + anim.width, anim.y + anim.height),  # Bottom-right
        ]

        bracket_configs = [
            ((-1, -1), [(corner_len, 0), (0, 0), (0, corner_len)]),  # Top-left
            ((1, -1), [(-corner_len, 0), (0, 0), (0, corner_len)]),  # Top-right
            ((-1, 1), [(corner_len, 0), (0, 0), (0, -corner_len)]),  # Bottom-left
            ((1, 1), [(-corner_len, 0), (0, 0), (0, -corner_len)]),  # Bottom-right
        ]

        for corner_idx, (corner_pos, path) in enumerate(zip(corners, bracket_configs)):
            cx, cy = corner_pos
            for i, (dx, dy) in enumerate(path):
                if i == 0:
                    ctx.move_to(cx + dx, cy + dy)
                else:
                    ctx.line_to(cx + dx, cy + dy)
            ctx.stroke()

        # Label
        if anim.label:
            ctx.set_font_size(12)
            extents = ctx.text_extents(anim.label)
            label_x = anim.x + anim.width / 2 - extents.width / 2
            label_y = anim.y - 8
            ctx.move_to(label_x, label_y)
            ctx.show_text(anim.label)

        ctx.restore()

    def _draw_scroll(self, ctx: Cairo.Context, anim: ScrollAnimation, current_time: float):
        """Draw scroll direction indicator with staggered chevron arrows."""
        progress = anim.progress(current_time)
        alpha = (1.0 - progress) * anim.color.a

        ctx.save()
        ctx.translate(anim.x, anim.y)
        ctx.set_line_width(2.0)
        ctx.set_line_cap(Cairo.LineCap.ROUND)
        ctx.set_line_join(Cairo.LineJoin.ROUND)

        # Three staggered chevrons
        chevron_size = anim.chevron_size
        spacing = chevron_size * 0.6
        y_direction = 1 if anim.direction == 'down' else -1

        for chevron_idx in range(3):
            # Cascade fade based on progress
            cascade_delay = chevron_idx * 0.1
            chevron_progress = max(0, min(1.0, (progress - cascade_delay) / 0.3))
            chevron_alpha = chevron_progress * (1.0 - progress) * alpha
            ctx.set_source_rgba(anim.color.r, anim.color.g, anim.color.b, chevron_alpha)

            y_offset = chevron_idx * spacing * y_direction

            # Draw chevron (">")
            if anim.direction == 'down':
                ctx.move_to(-chevron_size/2, y_offset)
                ctx.line_to(0, y_offset + chevron_size)
                ctx.line_to(chevron_size/2, y_offset)
            else:  # up
                ctx.move_to(-chevron_size/2, y_offset + chevron_size)
                ctx.line_to(0, y_offset)
                ctx.line_to(chevron_size/2, y_offset + chevron_size)

            ctx.stroke()

        ctx.restore()

    def _draw_rounded_rect(self, ctx: Cairo.Context, x: float, y: float,
                          width: float, height: float, radius: float):
        """Helper to draw rounded rectangle."""
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
        """Remove completed animations."""
        for anim_type in self.animations:
            self.animations[anim_type] = [
                anim for anim in self.animations[anim_type]
                if not anim.is_complete(current_time)
            ]

    def _tick(self) -> bool:
        """60 FPS refresh tick."""
        if self.running:
            self.queue_draw()
        return self.running

    def _check_idle_timeout(self) -> bool:
        """Check for 120s idle timeout."""
        if time.time() - self.last_input_time > 120:
            print("[overlay] Idle timeout (120s) - exiting", file=sys.stderr)
            self.quit()
            return False
        return True

    def on_destroy(self, widget):
        """Cleanup on window close."""
        self.running = False
        if self.stdin_handler_id is not None:
            GLib.source_remove(self.stdin_handler_id)
        Gtk.main_quit()

    def quit(self):
        """Graceful shutdown."""
        self.running = False
        Gtk.main_quit()


def main():
    """Entry point."""
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

    window = OverlayWindow()
    window.show()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

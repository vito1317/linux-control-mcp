/**
 * Keyboard Control Tools
 * Provides MCP tools for keyboard interaction
 */

import { z } from 'zod';
import { execPython } from '../utils/python-bridge.js';
import { showTypeAnimation } from '../utils/overlay-bridge.js';
import { Point } from '../types/index.js';

const KeyboardTypeSchema = z.object({
  text: z.string().describe('Text to type'),
});

const KeyboardPressSchema = z.object({
  key: z.string().describe('Key name (a-z, 0-9, return, tab, etc)'),
  modifiers: z
    .array(z.enum(['cmd', 'shift', 'alt', 'ctrl', 'fn']))
    .optional()
    .describe('Modifier keys'),
});

const KeyboardHotkeySchema = z.object({
  keys: z.string().describe('Hotkey combination with + separator (e.g., cmd+c, ctrl+shift+z)'),
});

/**
 * Get the position of the caret (text cursor)
 */
async function getCaretPosition(): Promise<Point | null> {
  try {
    const result = await execPython('accessibility', 'caret-position');
    if (result.success && result.data) {
      return result.data as Point;
    }
  } catch {
    // Caret position detection not critical
  }
  return null;
}

export const keyboardTypeToolDefinition = {
  description: 'Type a string of text character by character, simulating real keyboard input',
  schema: KeyboardTypeSchema,
  handler: async (input: z.infer<typeof KeyboardTypeSchema>) => {
    // Try to get caret position for animation
    const caretPos = await getCaretPosition();

    if (caretPos) {
      // Show typing animation at caret position
      await showTypeAnimation(caretPos.x, caretPos.y, input.text).catch(() => {});
    }

    // Execute the typing
    const result = await execPython('keyboard', 'type', input.text);

    return result;
  },
};

export const keyboardPressToolDefinition = {
  description: 'Press a key with optional modifier keys',
  schema: KeyboardPressSchema,
  handler: async (input: z.infer<typeof KeyboardPressSchema>) => {
    const args = [input.key];
    if (input.modifiers && input.modifiers.length > 0) {
      args.push(JSON.stringify(input.modifiers));
    }

    const result = await execPython('keyboard', 'press', ...args);

    return result;
  },
};

export const keyboardHotkeyToolDefinition = {
  description: 'Press a keyboard shortcut / hotkey combination',
  schema: KeyboardHotkeySchema,
  handler: async (input: z.infer<typeof KeyboardHotkeySchema>) => {
    // Try to get caret position for visual feedback
    const caretPos = await getCaretPosition();

    if (caretPos) {
      // Show typing animation showing the hotkey
      await showTypeAnimation(caretPos.x, caretPos.y, input.keys).catch(() => {});
    }

    // Execute the hotkey
    const result = await execPython('keyboard', 'hotkey', input.keys);

    return result;
  },
};

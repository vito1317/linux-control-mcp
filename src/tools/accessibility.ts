/**
 * Accessibility Tools
 * Provides MCP tools for accessibility tree and element interaction
 */

import { z } from 'zod';
import { execPython } from '../utils/python-bridge.js';

const AccessibilityCheckSchema = z.object({});

const AccessibilityTreeSchema = z.object({
  maxDepth: z.number().optional().default(3).describe('Maximum depth of tree'),
  interactive: z
    .boolean()
    .optional()
    .default(false)
    .describe('Only return interactive elements'),
});

const AccessibilityElementAtSchema = z.object({
  x: z.number().describe('X coordinate'),
  y: z.number().describe('Y coordinate'),
});

const AccessibilityClickSchema = z.object({
  role: z.string().describe('Accessibility role (e.g., AXButton, AXMenuItem)'),
  title: z.string().optional().describe('Element title to match'),
});

export const accessibilityCheckToolDefinition = {
  description: 'Check if Accessibility permissions are granted',
  schema: AccessibilityCheckSchema,
  handler: async () => {
    return execPython('accessibility', 'check');
  },
};

export const accessibilityTreeToolDefinition = {
  description: 'Get the accessibility tree of the frontmost application',
  schema: AccessibilityTreeSchema,
  handler: async (input: z.infer<typeof AccessibilityTreeSchema>) => {
    return execPython(
      'accessibility',
      'tree',
      '--max-depth',
      String(input.maxDepth),
      '--interactive',
      String(input.interactive)
    );
  },
};

export const accessibilityElementAtToolDefinition = {
  description: 'Get the UI element at a specific screen coordinate',
  schema: AccessibilityElementAtSchema,
  handler: async (input: z.infer<typeof AccessibilityElementAtSchema>) => {
    return execPython('accessibility', 'element-at', String(input.x), String(input.y));
  },
};

export const accessibilityClickToolDefinition = {
  description: 'Click a UI element by its accessibility role and optional title',
  schema: AccessibilityClickSchema,
  handler: async (input: z.infer<typeof AccessibilityClickSchema>) => {
    const args = [input.role];
    if (input.title) {
      args.push('--title', input.title);
    }

    return execPython('accessibility', 'click', ...args);
  },
};

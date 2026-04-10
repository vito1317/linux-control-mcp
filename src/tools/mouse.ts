/**
 * Mouse Control Tools
 * Provides MCP tools for mouse interaction
 */

import { z } from 'zod';
import { execPython } from '../utils/python-bridge.js';
import {
  showClickAnimation,
  showTrailAnimation,
  showScrollAnimation,
} from '../utils/overlay-bridge.js';
import { Point } from '../types/index.js';

/**
 * Generate an easing curve for animation
 */
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * Generate animation trail points with easing
 */
function generateTrailPoints(from: Point, to: Point, steps: number = 10): Point[] {
  const points: Point[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const eased = easeOutCubic(t);
    points.push({
      x: Math.round(from.x + (to.x - from.x) * eased),
      y: Math.round(from.y + (to.y - from.y) * eased),
    });
  }
  return points;
}

const MouseMoveSchema = z.object({
  x: z.number().describe('X coordinate'),
  y: z.number().describe('Y coordinate'),
});

const MouseClickSchema = z.object({
  x: z.number().describe('X coordinate'),
  y: z.number().describe('Y coordinate'),
  button: z
    .enum(['left', 'right', 'middle'])
    .optional()
    .default('left')
    .describe('Mouse button'),
  clicks: z.number().int().min(1).max(3).optional().default(1).describe('Number of clicks'),
});

const MouseDragSchema = z.object({
  fromX: z.number().describe('Starting X coordinate'),
  fromY: z.number().describe('Starting Y coordinate'),
  toX: z.number().describe('Ending X coordinate'),
  toY: z.number().describe('Ending Y coordinate'),
  duration: z
    .number()
    .optional()
    .default(0.5)
    .describe('Duration of drag in seconds'),
});

const MouseScrollSchema = z.object({
  x: z.number().describe('X coordinate to scroll at'),
  y: z.number().describe('Y coordinate to scroll at'),
  deltaY: z.number().describe('Vertical scroll amount (positive=down, negative=up)'),
  deltaX: z
    .number()
    .optional()
    .default(0)
    .describe('Horizontal scroll amount'),
});

const MousePositionSchema = z.object({});

export const mouseMoveToolDefinition = {
  description: 'Move the mouse cursor to specified screen coordinates',
  schema: MouseMoveSchema,
  handler: async (input: z.infer<typeof MouseMoveSchema>) => {
    const result = await execPython('mouse', 'move', String(input.x), String(input.y));

    if (result.success) {
      // Show trail animation
      const trailPoints = generateTrailPoints({ x: input.x, y: input.y }, { x: input.x, y: input.y });
      await showTrailAnimation(trailPoints).catch(() => {
        // Animation failures shouldn't break functionality
      });
    }

    return result;
  },
};

export const mouseClickToolDefinition = {
  description: 'Click the mouse at specified coordinates',
  schema: MouseClickSchema,
  handler: async (input: z.infer<typeof MouseClickSchema>) => {
    // Get current position first (if available)
    const currentPosResult = await execPython('mouse', 'position');
    const currentPos = currentPosResult.success
      ? (currentPosResult.data as Point)
      : { x: input.x, y: input.y };

    // Show trail animation from current position to target
    const trailPoints = generateTrailPoints(currentPos, { x: input.x, y: input.y });
    await showTrailAnimation(trailPoints).catch(() => {});

    // Wait a bit for trail animation, then show click
    await new Promise((resolve) => setTimeout(resolve, 300));

    // Show click ripple
    await showClickAnimation(input.x, input.y, {
      button: input.button,
      duration: 0.3,
    }).catch(() => {});

    // Execute the click
    const result = await execPython('mouse', 'click', String(input.x), String(input.y), input.button, String(input.clicks));

    return result;
  },
};

export const mouseDragToolDefinition = {
  description: 'Drag the mouse from one position to another',
  schema: MouseDragSchema,
  handler: async (input: z.infer<typeof MouseDragSchema>) => {
    // Show drag trail animation
    const trailPoints = generateTrailPoints(
      { x: input.fromX, y: input.fromY },
      { x: input.toX, y: input.toY },
      20
    );
    await showTrailAnimation(trailPoints, {
      duration: input.duration,
    }).catch(() => {});

    // Execute the drag
    const result = await execPython(
      'mouse',
      'drag',
      String(input.fromX),
      String(input.fromY),
      String(input.toX),
      String(input.toY),
      String(input.duration)
    );

    return result;
  },
};

export const mouseScrollToolDefinition = {
  description: 'Scroll at specified coordinates',
  schema: MouseScrollSchema,
  handler: async (input: z.infer<typeof MouseScrollSchema>) => {
    // Show scroll indicator
    const direction = input.deltaY > 0 ? 'down' : 'up';
    await showScrollAnimation(input.x, input.y, direction).catch(() => {});

    // Execute scroll
    const result = await execPython(
      'mouse',
      'scroll',
      String(input.x),
      String(input.y),
      String(input.deltaY),
      String(input.deltaX)
    );

    return result;
  },
};

export const mousePositionToolDefinition = {
  description: 'Get the current mouse cursor position',
  schema: MousePositionSchema,
  handler: async () => {
    return execPython('mouse', 'position');
  },
};

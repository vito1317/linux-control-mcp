/**
 * Animation Tools
 * Provides MCP tools for visual feedback animations
 */

import { z } from 'zod';
import {
  showClickAnimation,
  showTrailAnimation,
  showTypeAnimation,
  showHighlightAnimation,
  showScrollAnimation,
} from '../utils/overlay-bridge.js';
import { Point } from '../types/index.js';

const AnimationClickSchema = z.object({
  x: z.number().describe('X coordinate'),
  y: z.number().describe('Y coordinate'),
  button: z
    .enum(['left', 'right', 'double'])
    .optional()
    .default('left')
    .describe('Click style visual'),
  color: z.string().optional().default('#007AFF').describe('Hex color'),
});

const AnimationTrailSchema = z.object({
  points: z
    .array(z.object({ x: z.number(), y: z.number() }))
    .describe('Array of [x,y] coordinate pairs forming the path'),
  color: z.string().optional().default('#34C759').describe('Hex color'),
  duration: z.number().optional().default(1.5).describe('Animation duration in seconds'),
});

const AnimationTypeSchema = z.object({
  x: z.number().describe('X coordinate'),
  y: z.number().describe('Y coordinate'),
  text: z.string().describe('Text to display in the typing animation'),
  color: z.string().optional().default('#AF52DE').describe('Hex color'),
});

const AnimationHighlightSchema = z.object({
  x: z.number().describe('X coordinate of top-left corner'),
  y: z.number().describe('Y coordinate of top-left corner'),
  width: z.number().describe('Width of the highlight region'),
  height: z.number().describe('Height of the highlight region'),
  color: z.string().optional().default('#FF9500').describe('Hex color'),
  label: z.string().optional().describe('Label text to show above the highlight'),
  duration: z.number().optional().default(2).describe('Duration in seconds'),
});

const AnimationScrollSchema = z.object({
  x: z.number().describe('X coordinate'),
  y: z.number().describe('Y coordinate'),
  direction: z
    .enum(['up', 'down'])
    .describe('Scroll direction'),
  color: z.string().optional().default('#5AC8FA').describe('Hex color'),
});

export const animationClickToolDefinition = {
  description: 'Show a visual click ripple animation at specified coordinates',
  inputSchema: {
    type: 'object' as const,
    properties: {
      x: {
        type: 'number' as const,
        description: 'X coordinate',
      },
      y: {
        type: 'number' as const,
        description: 'Y coordinate',
      },
      button: {
        type: 'string' as const,
        enum: ['left', 'right', 'double'],
        description: 'Click style visual',
      },
      color: {
        type: 'string' as const,
        description: 'Hex color (default: #007AFF)',
      },
    },
    required: ['x', 'y'],
  },
  handler: async (input: z.infer<typeof AnimationClickSchema>) => {
    try {
      await showClickAnimation(input.x, input.y, {
        button: input.button,
        color: input.color,
      });

      return {
        success: true,
        data: {
          message: 'Click animation displayed',
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Animation failed: ${errorMsg}`,
      };
    }
  },
};

export const animationTrailToolDefinition = {
  description: 'Show a visual mouse movement trail animation along a path',
  inputSchema: {
    type: 'object' as const,
    properties: {
      points: {
        type: 'array' as const,
        items: {
          type: 'object' as const,
          properties: {
            x: { type: 'number' as const },
            y: { type: 'number' as const },
          },
          required: ['x', 'y'],
        },
        description: 'Array of coordinate pairs forming the path',
      },
      color: {
        type: 'string' as const,
        description: 'Hex color',
      },
      duration: {
        type: 'number' as const,
        description: 'Animation duration in seconds',
      },
    },
    required: ['points'],
  },
  handler: async (input: z.infer<typeof AnimationTrailSchema>) => {
    try {
      const points: Point[] = input.points.map((p) => ({ x: p.x, y: p.y }));

      await showTrailAnimation(points, {
        color: input.color,
        duration: input.duration,
      });

      return {
        success: true,
        data: {
          message: 'Trail animation displayed',
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Animation failed: ${errorMsg}`,
      };
    }
  },
};

export const animationTypeToolDefinition = {
  description: 'Show a visual typing indicator animation with text',
  inputSchema: {
    type: 'object' as const,
    properties: {
      x: {
        type: 'number' as const,
        description: 'X coordinate',
      },
      y: {
        type: 'number' as const,
        description: 'Y coordinate',
      },
      text: {
        type: 'string' as const,
        description: 'Text to display in the typing animation',
      },
      color: {
        type: 'string' as const,
        description: 'Hex color',
      },
    },
    required: ['x', 'y', 'text'],
  },
  handler: async (input: z.infer<typeof AnimationTypeSchema>) => {
    try {
      await showTypeAnimation(input.x, input.y, input.text, {
        color: input.color,
      });

      return {
        success: true,
        data: {
          message: 'Type animation displayed',
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Animation failed: ${errorMsg}`,
      };
    }
  },
};

export const animationHighlightToolDefinition = {
  description: 'Show a visual highlight animation on a rectangular region',
  inputSchema: {
    type: 'object' as const,
    properties: {
      x: {
        type: 'number' as const,
        description: 'X coordinate of top-left corner',
      },
      y: {
        type: 'number' as const,
        description: 'Y coordinate of top-left corner',
      },
      width: {
        type: 'number' as const,
        description: 'Width of the highlight region',
      },
      height: {
        type: 'number' as const,
        description: 'Height of the highlight region',
      },
      color: {
        type: 'string' as const,
        description: 'Hex color',
      },
      label: {
        type: 'string' as const,
        description: 'Label text to show',
      },
      duration: {
        type: 'number' as const,
        description: 'Duration in seconds',
      },
    },
    required: ['x', 'y', 'width', 'height'],
  },
  handler: async (input: z.infer<typeof AnimationHighlightSchema>) => {
    try {
      await showHighlightAnimation(input.x, input.y, input.width, input.height, {
        color: input.color,
        label: input.label,
        duration: input.duration,
      });

      return {
        success: true,
        data: {
          message: 'Highlight animation displayed',
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Animation failed: ${errorMsg}`,
      };
    }
  },
};

export const animationScrollToolDefinition = {
  description: 'Show a visual scroll direction indicator animation',
  inputSchema: {
    type: 'object' as const,
    properties: {
      x: {
        type: 'number' as const,
        description: 'X coordinate',
      },
      y: {
        type: 'number' as const,
        description: 'Y coordinate',
      },
      direction: {
        type: 'string' as const,
        enum: ['up', 'down'],
        description: 'Scroll direction',
      },
      color: {
        type: 'string' as const,
        description: 'Hex color',
      },
    },
    required: ['x', 'y', 'direction'],
  },
  handler: async (input: z.infer<typeof AnimationScrollSchema>) => {
    try {
      await showScrollAnimation(input.x, input.y, input.direction as 'up' | 'down', {
        color: input.color,
      });

      return {
        success: true,
        data: {
          message: 'Scroll animation displayed',
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Animation failed: ${errorMsg}`,
      };
    }
  },
};

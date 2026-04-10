/**
 * Screenshot Tools
 * Provides MCP tools for screen capture and analysis
 */

import { z } from 'zod';
import { execPython } from '../utils/python-bridge.js';
import {
  addCoordinateGrid,
  optimizeForAI,
  cropRegion,
  annotatePoints,
} from '../utils/image.js';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { Rect } from '../types/index.js';

const ScreenshotSchema = z.object({
  region: z
    .object({
      x: z.number(),
      y: z.number(),
      width: z.number(),
      height: z.number(),
    })
    .optional()
    .describe('Capture specific region (x, y, width, height)'),
  showGrid: z.boolean().optional().default(false).describe('Overlay coordinate grid'),
  gridSpacing: z.number().optional().default(100).describe('Grid line spacing in pixels'),
  quality: z.number().int().min(1).max(100).optional().default(80).describe('Image quality (1-100)'),
  format: z.enum(['png', 'jpeg']).optional().default('png').describe('Output format'),
  maxWidth: z.number().optional().describe('Max width for AI optimization'),
});

const ScreenshotAnnotatedSchema = z.object({
  points: z
    .array(
      z.object({
        x: z.number(),
        y: z.number(),
        label: z.string().optional(),
        color: z.string().optional(),
      })
    )
    .describe('Points to annotate on the screenshot'),
  region: z
    .object({
      x: z.number(),
      y: z.number(),
      width: z.number(),
      height: z.number(),
    })
    .optional()
    .describe('Capture specific region'),
  quality: z.number().int().min(1).max(100).optional().default(80).describe('Image quality'),
  maxWidth: z.number().optional().describe('Max width for optimization'),
});

const ScreenInfoSchema = z.object({});

/**
 * Capture screenshot via python helper and process it
 */
async function captureScreenshot(region?: Rect): Promise<Buffer> {
  // Use a temp file for exchange
  const tempDir = os.tmpdir();
  const tempFile = path.join(tempDir, `screenshot-${Date.now()}.png`);

  try {
    // Call python helper: screen screenshot <filepath> [x y w h]
    const args: string[] = [tempFile];
    if (region) {
      args.push(String(region.x), String(region.y), String(region.width), String(region.height));
    }

    const result = await execPython('screen', 'screenshot', ...args);

    if (!result.success) {
      throw new Error(result.error || 'Failed to capture screenshot');
    }

    // Read the captured image
    const imageBuffer = await fs.readFile(tempFile);

    // Clean up temp file
    await fs.unlink(tempFile).catch(() => {});

    return imageBuffer;
  } catch (error) {
    // Clean up on error
    await fs.unlink(tempFile).catch(() => {});
    throw error;
  }
}

export const screenshotToolDefinition = {
  description: 'Take a screenshot of the entire screen or a specific region',
  inputSchema: {
    type: 'object' as const,
    properties: {
      region: {
        type: 'object' as const,
        properties: {
          x: { type: 'number' as const },
          y: { type: 'number' as const },
          width: { type: 'number' as const },
          height: { type: 'number' as const },
        },
        description: 'Capture specific region (x, y, width, height)',
      },
      showGrid: {
        type: 'boolean' as const,
        description: 'Overlay coordinate grid',
      },
      gridSpacing: {
        type: 'number' as const,
        description: 'Grid line spacing in pixels',
      },
      quality: {
        type: 'number' as const,
        description: 'Image quality (1-100)',
      },
      format: {
        type: 'string' as const,
        enum: ['png', 'jpeg'],
        description: 'Output format',
      },
      maxWidth: {
        type: 'number' as const,
        description: 'Max width for AI optimization',
      },
    },
  },
  handler: async (input: z.infer<typeof ScreenshotSchema>) => {
    try {
      // Capture the screenshot
      let imageBuffer = await captureScreenshot(input.region);

      // Add grid if requested
      if (input.showGrid) {
        imageBuffer = await addCoordinateGrid(imageBuffer, {
          spacing: input.gridSpacing,
        });
      }

      // Optimize for AI if maxWidth is specified
      if (input.maxWidth) {
        imageBuffer = await optimizeForAI(imageBuffer, {
          maxWidth: input.maxWidth,
          quality: input.quality,
        });
      }

      // Convert to base64 for transmission
      const base64 = imageBuffer.toString('base64');

      return {
        success: true,
        data: {
          image: base64,
          format: input.format,
          mimeType: input.format === 'png' ? 'image/png' : 'image/jpeg',
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Screenshot capture failed: ${errorMsg}`,
      };
    }
  },
};

export const screenshotAnnotatedToolDefinition = {
  description: 'Take a screenshot and annotate specific points with labels',
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
            label: { type: 'string' as const },
            color: { type: 'string' as const },
          },
          required: ['x', 'y'],
        },
        description: 'Points to annotate',
      },
      region: {
        type: 'object' as const,
        properties: {
          x: { type: 'number' as const },
          y: { type: 'number' as const },
          width: { type: 'number' as const },
          height: { type: 'number' as const },
        },
        description: 'Capture specific region',
      },
      quality: {
        type: 'number' as const,
        description: 'Image quality',
      },
      maxWidth: {
        type: 'number' as const,
        description: 'Max width for optimization',
      },
    },
    required: ['points'],
  },
  handler: async (input: z.infer<typeof ScreenshotAnnotatedSchema>) => {
    try {
      // Capture screenshot
      let imageBuffer = await captureScreenshot(input.region);

      // Annotate points
      imageBuffer = await annotatePoints(imageBuffer, input.points);

      // Optimize if needed
      if (input.maxWidth) {
        imageBuffer = await optimizeForAI(imageBuffer, {
          maxWidth: input.maxWidth,
          quality: input.quality,
        });
      }

      const base64 = imageBuffer.toString('base64');

      return {
        success: true,
        data: {
          image: base64,
          format: 'png',
          mimeType: 'image/png',
          pointsCount: input.points.length,
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Annotated screenshot failed: ${errorMsg}`,
      };
    }
  },
};

export const screenInfoToolDefinition = {
  description: 'Get information about all connected displays/screens',
  inputSchema: {
    type: 'object' as const,
    properties: {},
    required: [],
  },
  handler: async () => {
    return execPython('screen', 'info');
  },
};

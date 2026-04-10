/**
 * AI Optimization Tools
 * Provides MCP tools for AI-optimized screen analysis
 */

import { z } from 'zod';
import { execPython } from '../utils/python-bridge.js';
import {
  addCoordinateGrid,
  optimizeForAI,
  annotatePoints,
} from '../utils/image.js';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

const AIScreenContextSchema = z.object({
  gridSpacing: z.number().optional().default(100).describe('Grid spacing in pixels'),
  includeAccessibility: z
    .boolean()
    .optional()
    .default(true)
    .describe('Include accessibility tree'),
  includeScreenshot: z
    .boolean()
    .optional()
    .default(true)
    .describe('Include screenshot image'),
  maxWidth: z.number().optional().default(1280).describe('Max screenshot width'),
});

const AIFindElementSchema = z.object({
  query: z.string().describe('Natural language description of element to find'),
});

const AIOCRRegionSchema = z.object({
  x: z.number().describe('Region X coordinate'),
  y: z.number().describe('Region Y coordinate'),
  width: z.number().describe('Region width'),
  height: z.number().describe('Region height'),
});

const AIScreenElementsSchema = z.object({
  maxWidth: z.number().optional().default(1440).describe('Max screenshot width'),
});

const ClipboardReadSchema = z.object({});

const ClipboardWriteSchema = z.object({
  text: z.string().describe('Text to copy to clipboard'),
});

export const aiScreenContextToolDefinition = {
  description: 'Capture comprehensive snapshot of current screen state for AI analysis',
  schema: AIScreenContextSchema,
  handler: async (input: z.infer<typeof AIScreenContextSchema>) => {
    try {
      const tempDir = os.tmpdir();
      const tempFile = path.join(tempDir, `ai-context-${Date.now()}.png`);

      const result = await execPython('screen', 'screenshot', tempFile);

      if (!result.success) {
        return {
          success: false,
          error: 'Failed to capture screenshot',
        };
      }

      let screenshot: string | undefined;

      if (input.includeScreenshot) {
        let imageBuffer: Buffer = await fs.readFile(tempFile);

        // Add grid if requested
        imageBuffer = Buffer.from(await addCoordinateGrid(imageBuffer, {
          spacing: input.gridSpacing,
        }));

        // Optimize for AI
        imageBuffer = Buffer.from(await optimizeForAI(imageBuffer, {
          maxWidth: input.maxWidth,
        }));

        screenshot = imageBuffer.toString('base64');

        // Clean up
        await fs.unlink(tempFile).catch(() => {});
      }

      // Get accessibility tree
      let accessibility = undefined;
      if (input.includeAccessibility) {
        const a11yResult = await execPython('accessibility', 'tree', '--max-depth', '3');
        if (a11yResult.success) {
          accessibility = a11yResult.data;
        }
      }

      // Get mouse position
      const posResult = await execPython('mouse', 'position');
      const mousePosition = posResult.success ? posResult.data : undefined;

      // Get screen info
      const screenResult = await execPython('screen', 'info');
      const screenInfo = screenResult.success ? screenResult.data : undefined;

      return {
        success: true,
        data: {
          screenshot,
          accessibility,
          mousePosition,
          screenInfo,
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `AI screen context failed: ${errorMsg}`,
      };
    }
  },
};

export const aiFindElementToolDefinition = {
  description: 'Find a UI element by natural language description',
  schema: AIFindElementSchema,
  handler: async (input: z.infer<typeof AIFindElementSchema>) => {
    return execPython('accessibility', 'find', input.query);
  },
};

export const aiOCRRegionToolDefinition = {
  description: 'Extract text from a screen region using OCR',
  schema: AIOCRRegionSchema,
  handler: async (input: z.infer<typeof AIOCRRegionSchema>) => {
    return execPython(
      'ocr',
      'region',
      String(input.x),
      String(input.y),
      String(input.width),
      String(input.height)
    );
  },
};

export const aiScreenElementsToolDefinition = {
  description: 'Scan all interactive elements on screen with auto-detected annotations',
  schema: AIScreenElementsSchema,
  handler: async (input: z.infer<typeof AIScreenElementsSchema>) => {
    try {
      const tempDir = os.tmpdir();
      const tempFile = path.join(tempDir, `ai-elements-${Date.now()}.png`);

      // Capture screenshot
      const captureResult = await execPython('screen', 'screenshot', tempFile);

      if (!captureResult.success) {
        return {
          success: false,
          error: 'Failed to capture screenshot',
        };
      }

      // Get interactive elements
      const elementsResult = await execPython('accessibility', 'interactive-elements');

      if (!elementsResult.success) {
        await fs.unlink(tempFile).catch(() => {});
        return elementsResult;
      }

      // Annotate image with elements
      let imageBuffer: Buffer = await fs.readFile(tempFile);

      const elements = (elementsResult.data as Array<{ x: number; y: number; label?: string }>) || [];
      imageBuffer = Buffer.from(await annotatePoints(
        imageBuffer,
        elements.map((el, idx) => ({
          x: el.x,
          y: el.y,
          label: String(idx + 1),
          color: '#007AFF',
        }))
      ));

      // Optimize
      imageBuffer = Buffer.from(await optimizeForAI(imageBuffer, {
        maxWidth: input.maxWidth,
      }));

      const screenshot = imageBuffer.toString('base64');

      // Clean up
      await fs.unlink(tempFile).catch(() => {});

      return {
        success: true,
        data: {
          screenshot,
          elements,
          elementCount: elements.length,
        },
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Screen elements analysis failed: ${errorMsg}`,
      };
    }
  },
};

export const clipboardReadToolDefinition = {
  description: 'Read the current text content from the clipboard',
  schema: ClipboardReadSchema,
  handler: async () => {
    return execPython('clipboard', 'read');
  },
};

export const clipboardWriteToolDefinition = {
  description: 'Write text content to the clipboard',
  schema: ClipboardWriteSchema,
  handler: async (input: z.infer<typeof ClipboardWriteSchema>) => {
    return execPython('clipboard', 'write', input.text);
  },
};

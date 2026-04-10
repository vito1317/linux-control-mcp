/**
 * Window Control Tools
 * Provides MCP tools for window and application management
 */

import { z } from 'zod';
import { execPython } from '../utils/python-bridge.js';

const WindowListSchema = z.object({});

const WindowFocusSchema = z.object({
  appName: z.string().describe('Application name to focus'),
});

const WindowResizeSchema = z.object({
  appName: z.string().describe('Application name'),
  x: z.number().describe('New X position'),
  y: z.number().describe('New Y position'),
  width: z.number().describe('New width'),
  height: z.number().describe('New height'),
});

const WindowMinimizeSchema = z.object({
  appName: z.string().describe('Application name'),
});

const WindowCloseSchema = z.object({
  appName: z.string().describe('Application name'),
});

const AppsListSchema = z.object({});

export const windowListToolDefinition = {
  description: 'List all visible windows on screen',
  inputSchema: {
    type: 'object' as const,
    properties: {},
    required: [],
  },
  handler: async () => {
    return execPython('window', 'list');
  },
};

export const windowFocusToolDefinition = {
  description: 'Bring an application to the foreground and focus it',
  inputSchema: {
    type: 'object' as const,
    properties: {
      appName: {
        type: 'string' as const,
        description: 'Application name (e.g., Safari, Terminal, VS Code)',
      },
    },
    required: ['appName'],
  },
  handler: async (input: z.infer<typeof WindowFocusSchema>) => {
    return execPython('window', 'focus', input.appName);
  },
};

export const windowResizeToolDefinition = {
  description: 'Move and resize an application window',
  inputSchema: {
    type: 'object' as const,
    properties: {
      appName: {
        type: 'string' as const,
        description: 'Application name',
      },
      x: {
        type: 'number' as const,
        description: 'New X position',
      },
      y: {
        type: 'number' as const,
        description: 'New Y position',
      },
      width: {
        type: 'number' as const,
        description: 'New width',
      },
      height: {
        type: 'number' as const,
        description: 'New height',
      },
    },
    required: ['appName', 'x', 'y', 'width', 'height'],
  },
  handler: async (input: z.infer<typeof WindowResizeSchema>) => {
    return execPython(
      'window',
      'resize',
      input.appName,
      String(input.x),
      String(input.y),
      String(input.width),
      String(input.height)
    );
  },
};

export const windowMinimizeToolDefinition = {
  description: 'Minimize the front window of an application',
  inputSchema: {
    type: 'object' as const,
    properties: {
      appName: {
        type: 'string' as const,
        description: 'Application name',
      },
    },
    required: ['appName'],
  },
  handler: async (input: z.infer<typeof WindowMinimizeSchema>) => {
    return execPython('window', 'minimize', input.appName);
  },
};

export const windowCloseToolDefinition = {
  description: 'Close the front window of an application',
  inputSchema: {
    type: 'object' as const,
    properties: {
      appName: {
        type: 'string' as const,
        description: 'Application name',
      },
    },
    required: ['appName'],
  },
  handler: async (input: z.infer<typeof WindowCloseSchema>) => {
    return execPython('window', 'close', input.appName);
  },
};

export const appsListToolDefinition = {
  description: 'List all running applications with their name, PID, and status',
  inputSchema: {
    type: 'object' as const,
    properties: {},
    required: [],
  },
  handler: async () => {
    return execPython('apps', 'list');
  },
};

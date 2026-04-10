/**
 * Terminal Control Tools
 * Provides MCP tools for executing shell commands
 */

import { z } from 'zod';
import { execPython } from '../utils/python-bridge.js';

const TerminalExecuteSchema = z.object({
  command: z.string().describe('Shell command to execute'),
  cwd: z.string().optional().describe('Working directory'),
  shell: z.string().optional().default('/bin/bash').describe('Shell to use'),
  timeout: z.number().optional().default(30000).describe('Timeout in milliseconds'),
  env: z
    .record(z.string())
    .optional()
    .describe('Additional environment variables'),
});

const TerminalExecuteBackgroundSchema = z.object({
  command: z.string().describe('Command to run in background'),
  cwd: z.string().optional().describe('Working directory'),
});

const TerminalScriptSchema = z.object({
  command: z.string().describe('Shell command or script to execute'),
  cwd: z.string().optional().describe('Working directory'),
  shell: z.string().optional().default('/bin/bash').describe('Shell to use'),
  timeout: z.number().optional().default(30000).describe('Timeout in milliseconds'),
});

export const terminalExecuteToolDefinition = {
  description: 'Execute a shell command and wait for completion',
  schema: TerminalExecuteSchema,
  handler: async (input: z.infer<typeof TerminalExecuteSchema>) => {
    const args = [
      input.command,
      '--cwd',
      input.cwd || process.env.HOME || '/tmp',
      '--shell',
      input.shell || '/bin/bash',
      '--timeout',
      String(input.timeout || 30000),
    ];

    if (input.env && Object.keys(input.env).length > 0) {
      args.push('--env');
      args.push(JSON.stringify(input.env));
    }

    const result = await execPython('terminal', 'execute', ...args);

    return result;
  },
};

export const terminalExecuteBackgroundToolDefinition = {
  description: 'Start a long-running process in the background',
  schema: TerminalExecuteBackgroundSchema,
  handler: async (input: z.infer<typeof TerminalExecuteBackgroundSchema>) => {
    const args = [input.command];

    if (input.cwd) {
      args.push('--cwd');
      args.push(input.cwd);
    }

    const result = await execPython('terminal', 'background', ...args);

    return result;
  },
};

export const terminalScriptToolDefinition = {
  description: 'Execute a bash/sh script (Linux equivalent of AppleScript)',
  schema: TerminalScriptSchema,
  handler: async (input: z.infer<typeof TerminalScriptSchema>) => {
    const args = [
      input.command,
      '--shell',
      input.shell || '/bin/bash',
      '--timeout',
      String(input.timeout || 30000),
    ];

    if (input.cwd) {
      args.push('--cwd');
      args.push(input.cwd);
    }

    const result = await execPython('terminal', 'script', ...args);

    return result;
  },
};

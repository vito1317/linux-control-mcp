/**
 * Python Helper Bridge
 * Executes the Linux control Python helper script and parses JSON output
 */

import { execFile } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { promisify } from 'util';
import { LinuxHelperResult } from '../types/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const execFileAsync = promisify(execFile);

let cachedHelperPath: string | null = null;

/**
 * Find the python helper script by searching common paths
 */
function findPythonHelper(): string {
  if (cachedHelperPath && existsSync(cachedHelperPath)) {
    return cachedHelperPath;
  }

  const searchPaths = [
    // Relative to dist/utils
    path.join(__dirname, '../../python-helpers/linux_control.py'),
    // Relative to src/utils (dev mode)
    path.join(__dirname, '../../../python-helpers/linux_control.py'),
    // Relative to cwd
    path.join(process.cwd(), 'python-helpers/linux_control.py'),
  ];

  for (const searchPath of searchPaths) {
    if (existsSync(searchPath)) {
      cachedHelperPath = searchPath;
      return searchPath;
    }
  }

  throw new Error(
    'Python helper (linux_control.py) not found. Searched paths: ' +
      searchPaths.join(', ')
  );
}

/**
 * Execute a python helper command
 * @param command Main command (e.g., 'mouse', 'keyboard', 'screenshot')
 * @param subcommand Subcommand (e.g., 'click', 'move', 'capture')
 * @param args Additional arguments
 * @returns Parsed JSON result from helper
 */
export async function execPython(
  command: string,
  subcommand: string,
  ...args: string[]
): Promise<LinuxHelperResult> {
  const helperPath = findPythonHelper();
  const cmdArgs = [subcommand, ...args];

  try {
    const { stdout, stderr } = await execFileAsync('python3', [helperPath, command, ...cmdArgs], {
      timeout: 30000, // 30 second timeout
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer
      encoding: 'utf-8',
    });

    if (stderr && stderr.trim()) {
      console.error(`[Python Helper] stderr from ${command} ${subcommand}:`, stderr);
    }

    try {
      const result = JSON.parse(stdout) as LinuxHelperResult;
      return result;
    } catch {
      return {
        success: false,
        error: `Failed to parse JSON output from helper: ${stdout.substring(0, 200)}`,
        output: stdout,
      };
    }
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    return {
      success: false,
      error: `Python helper execution failed: ${errorMsg}`,
    };
  }
}

/**
 * Check if the python helper is available
 */
export function isHelperAvailable(): boolean {
  try {
    findPythonHelper();
    return true;
  } catch {
    return false;
  }
}

/**
 * Execute a simple python command and return raw output
 */
export async function execPythonRaw(
  command: string,
  subcommand: string,
  ...args: string[]
): Promise<string> {
  const helperPath = findPythonHelper();
  const cmdArgs = [subcommand, ...args];

  try {
    const { stdout } = await execFileAsync('python3', [helperPath, command, ...cmdArgs], {
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024,
      encoding: 'utf-8',
    });

    return stdout;
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    throw new Error(`Python helper execution failed: ${errorMsg}`);
  }
}

/**
 * Get the python helper path (useful for debug)
 */
export function getPythonHelperPath(): string {
  return findPythonHelper();
}

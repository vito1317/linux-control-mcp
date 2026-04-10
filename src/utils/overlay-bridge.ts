/**
 * Overlay Process Bridge
 * Communicates with overlay.py for visual animations
 */

import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { existsSync } from 'fs';
import { Point, OverlayMessage, AnimationOptions } from '../types/index.js';

let overlayProcess: ChildProcess | null = null;
let overlayQueue: OverlayMessage[] = [];
let isInitializing = false;

/**
 * Find the overlay script
 */
function findOverlayScript(): string {
  const searchPaths = [
    path.join(__dirname, '../../python-helpers/overlay.py'),
    path.join(__dirname, '../../../python-helpers/overlay.py'),
    path.join(process.cwd(), 'python-helpers/overlay.py'),
  ];

  for (const searchPath of searchPaths) {
    if (existsSync(searchPath)) {
      return searchPath;
    }
  }

  throw new Error('Overlay script (overlay.py) not found. Searched paths: ' + searchPaths.join(', '));
}

/**
 * Ensure the overlay process is running
 */
export async function ensureOverlay(): Promise<void> {
  if (overlayProcess) {
    return;
  }

  if (isInitializing) {
    // Wait for initialization to complete
    await new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (overlayProcess) {
          clearInterval(checkInterval);
          resolve(undefined);
        }
      }, 100);
      setTimeout(() => {
        clearInterval(checkInterval);
        resolve(undefined);
      }, 5000);
    });
    return;
  }

  isInitializing = true;

  try {
    const overlayPath = findOverlayScript();
    overlayProcess = spawn('python3', [overlayPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        DISPLAY: process.env.DISPLAY || ':0',
        WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || '',
        XDG_RUNTIME_DIR: process.env.XDG_RUNTIME_DIR || '',
      },
    });

    overlayProcess.on('error', (err) => {
      console.error('Overlay process error:', err);
      overlayProcess = null;
    });

    overlayProcess.on('exit', (code) => {
      console.error(`Overlay process exited with code ${code}`);
      overlayProcess = null;
    });

    overlayProcess.stderr?.on('data', (data) => {
      console.error(`[Overlay stderr] ${data.toString().trim()}`);
    });

    overlayProcess.stdout?.on('data', (data) => {
      const lines = data.toString().split('\n').filter(Boolean);
      for (const line of lines) {
        if (line === 'READY') {
          isInitializing = false;
          // Process queued messages
          const queue = overlayQueue;
          overlayQueue = [];
          for (const msg of queue) {
            sendOverlayMessage(msg).catch((err) => console.error('Error sending queued message:', err));
          }
        }
      }
    });

    // Give the process time to start and become READY
    await new Promise<void>((resolve) => {
      const readyTimeout = setTimeout(() => {
        console.error('[Overlay] Timed out waiting for READY signal');
        resolve();
      }, 3000);

      const checkReady = () => {
        if (!isInitializing) {
          clearTimeout(readyTimeout);
          resolve();
        } else {
          setTimeout(checkReady, 100);
        }
      };
      setTimeout(checkReady, 200);
    });
  } catch (error) {
    console.error('Failed to start overlay process:', error);
    overlayProcess = null;
  } finally {
    isInitializing = false;
  }
}

/**
 * Send a message to the overlay process
 */
async function sendOverlayMessage(message: OverlayMessage): Promise<void> {
  await ensureOverlay();

  if (!overlayProcess?.stdin) {
    console.warn('Overlay process not available, queuing message');
    overlayQueue.push(message);
    return;
  }

  return new Promise((resolve, reject) => {
    const json = JSON.stringify(message) + '\n';
    overlayProcess!.stdin!.write(json, (err) => {
      if (err) {
        reject(err);
      } else {
        resolve();
      }
    });
  });
}

/**
 * Show a click animation at specified coordinates
 */
export async function showClickAnimation(
  x: number,
  y: number,
  options?: AnimationOptions & { duration?: number }
): Promise<void> {
  await sendOverlayMessage({
    action: 'click',
    x,
    y,
    options: {
      button: options?.button || 'left',
      color: options?.color || '#007AFF',
      duration: options?.duration || 0.5,
    },
  });
}

/**
 * Show a trail animation following a path
 */
export async function showTrailAnimation(
  points: Point[],
  options?: AnimationOptions & { duration?: number; width?: number }
): Promise<void> {
  await sendOverlayMessage({
    action: 'trail',
    points,
    options: {
      color: options?.color || '#34C759',
      duration: options?.duration || 1.5,
      width: options?.width || 2,
    },
  });
}

/**
 * Show a typing animation at specified coordinates
 */
export async function showTypeAnimation(
  x: number,
  y: number,
  text: string,
  options?: AnimationOptions & { duration?: number }
): Promise<void> {
  await sendOverlayMessage({
    action: 'type',
    x,
    y,
    text,
    options: {
      color: options?.color || '#AF52DE',
      duration: options?.duration || 1,
    },
  });
}

/**
 * Show a highlight animation on a rectangular region
 */
export async function showHighlightAnimation(
  x: number,
  y: number,
  width: number,
  height: number,
  options?: AnimationOptions & { label?: string; duration?: number }
): Promise<void> {
  await sendOverlayMessage({
    action: 'highlight',
    x,
    y,
    width,
    height,
    options: {
      color: options?.color || '#FF9500',
      label: options?.label,
      duration: options?.duration || 2,
    },
  });
}

/**
 * Show a scroll direction indicator animation
 */
export async function showScrollAnimation(
  x: number,
  y: number,
  direction: 'up' | 'down' | 'left' | 'right',
  options?: AnimationOptions & { duration?: number }
): Promise<void> {
  await sendOverlayMessage({
    action: 'scroll',
    x,
    y,
    direction,
    options: {
      color: options?.color || '#5AC8FA',
      duration: options?.duration || 1,
    },
  });
}

/**
 * Terminate the overlay process
 */
export function killOverlay(): void {
  if (overlayProcess) {
    overlayProcess.kill();
    overlayProcess = null;
  }
}

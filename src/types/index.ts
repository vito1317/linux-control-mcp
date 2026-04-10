/**
 * Linux Control MCP - Type Definitions
 * Mirrors macos-control-mcp but adapted for Linux accessibility APIs
 */

export interface LinuxHelperResult {
  success: boolean;
  data?: unknown;
  error?: string;
  output?: string;
}

export interface Point {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ScreenInfo {
  screens: {
    id: string;
    name: string;
    bounds: Rect;
    workarea: Rect;
    scale: number;
    primary: boolean;
  }[];
}

export interface WindowInfo {
  id: number;
  pid: number;
  name: string;
  title: string;
  bounds: Rect;
  visible: boolean;
  active: boolean;
  appName: string;
}

export interface AppInfo {
  name: string;
  pid: number;
  bundleId?: string;
  path?: string;
  active: boolean;
  hidden: boolean;
}

export interface AccessibilityNode {
  role: string;
  title?: string;
  value?: string;
  description?: string;
  bounds?: Rect;
  parent?: number;
  children?: number[];
  enabled: boolean;
  visible: boolean;
  focused: boolean;
  focusable: boolean;
  clickable: boolean;
  editable: boolean;
  scrollable: boolean;
  attributes?: Record<string, string>;
  actions?: string[];
}

export interface CoordinateGridOptions {
  spacing?: number;
  showGrid?: boolean;
  gridColor?: string;
  gridWidth?: number;
}

export interface TerminalResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  command: string;
}

export interface AnimationOptions {
  color?: string;
  duration?: number;
  button?: 'left' | 'right' | 'middle' | 'double';
  width?: number;
  label?: string;
}

export interface ImageProcessingOptions {
  maxWidth?: number;
  quality?: number;
  optimizeForAI?: boolean;
}

export interface ScreenshotOptions {
  region?: Rect;
  showGrid?: boolean;
  gridSpacing?: number;
  quality?: number;
  format?: 'png' | 'jpeg';
  maxWidth?: number;
}

export interface OverlayMessage {
  action: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  points?: Point[];
  text?: string;
  direction?: 'up' | 'down' | 'left' | 'right';
  options?: Record<string, unknown>;
}

export interface AccessibilityTreeOptions {
  maxDepth?: number;
  interactive?: boolean;
  includeHidden?: boolean;
}

export interface OCRResult {
  text: string;
  confidence: number;
  bounds?: Rect;
  words?: {
    text: string;
    confidence: number;
    bounds: Rect;
  }[];
}

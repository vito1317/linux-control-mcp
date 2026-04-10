/**
 * Linux Control MCP Server
 * Main server setup and tool registration
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

// Import all tool definitions
import { mouseMoveToolDefinition, mouseClickToolDefinition, mouseDragToolDefinition, mouseScrollToolDefinition, mousePositionToolDefinition } from './tools/mouse.js';
import { keyboardTypeToolDefinition, keyboardPressToolDefinition, keyboardHotkeyToolDefinition } from './tools/keyboard.js';
import { screenshotToolDefinition, screenshotAnnotatedToolDefinition, screenInfoToolDefinition } from './tools/screenshot.js';
import { terminalExecuteToolDefinition, terminalExecuteBackgroundToolDefinition, terminalScriptToolDefinition } from './tools/terminal.js';
import { windowListToolDefinition, windowFocusToolDefinition, windowResizeToolDefinition, windowMinimizeToolDefinition, windowCloseToolDefinition, appsListToolDefinition } from './tools/window.js';
import { accessibilityCheckToolDefinition, accessibilityTreeToolDefinition, accessibilityElementAtToolDefinition, accessibilityClickToolDefinition } from './tools/accessibility.js';
import { aiScreenContextToolDefinition, aiFindElementToolDefinition, aiOCRRegionToolDefinition, aiScreenElementsToolDefinition, clipboardReadToolDefinition, clipboardWriteToolDefinition } from './tools/ai-optimize.js';
import { animationClickToolDefinition, animationTrailToolDefinition, animationTypeToolDefinition, animationHighlightToolDefinition, animationScrollToolDefinition } from './tools/animation.js';

const server = new McpServer({
  name: 'linux-control-mcp',
  version: '1.0.0',
});

// Collect all tools into a flat map
const allTools: Record<string, { description: string; inputSchema: any; handler: (args: any) => Promise<any> }> = {
  // Mouse tools
  mouse_move: mouseMoveToolDefinition,
  mouse_click: mouseClickToolDefinition,
  mouse_drag: mouseDragToolDefinition,
  mouse_scroll: mouseScrollToolDefinition,
  mouse_position: mousePositionToolDefinition,

  // Keyboard tools
  keyboard_type: keyboardTypeToolDefinition,
  keyboard_press: keyboardPressToolDefinition,
  keyboard_hotkey: keyboardHotkeyToolDefinition,

  // Screenshot tools
  screenshot: screenshotToolDefinition,
  screenshot_annotated: screenshotAnnotatedToolDefinition,
  screen_info: screenInfoToolDefinition,

  // Terminal tools
  terminal_execute: terminalExecuteToolDefinition,
  terminal_execute_background: terminalExecuteBackgroundToolDefinition,
  terminal_script: terminalScriptToolDefinition,

  // Window tools
  window_list: windowListToolDefinition,
  window_focus: windowFocusToolDefinition,
  window_resize: windowResizeToolDefinition,
  window_minimize: windowMinimizeToolDefinition,
  window_close: windowCloseToolDefinition,
  apps_list: appsListToolDefinition,

  // Accessibility tools
  accessibility_check: accessibilityCheckToolDefinition,
  accessibility_tree: accessibilityTreeToolDefinition,
  accessibility_element_at: accessibilityElementAtToolDefinition,
  accessibility_click: accessibilityClickToolDefinition,

  // AI-optimized tools
  ai_screen_context: aiScreenContextToolDefinition,
  ai_find_element: aiFindElementToolDefinition,
  ai_ocr_region: aiOCRRegionToolDefinition,
  ai_screen_elements: aiScreenElementsToolDefinition,
  clipboard_read: clipboardReadToolDefinition,
  clipboard_write: clipboardWriteToolDefinition,

  // Animation tools
  animation_click: animationClickToolDefinition,
  animation_trail: animationTrailToolDefinition,
  animation_type: animationTypeToolDefinition,
  animation_highlight: animationHighlightToolDefinition,
  animation_scroll: animationScrollToolDefinition,
};

// Register all tools with the MCP server
for (const [name, tool] of Object.entries(allTools)) {
  server.tool(
    name,
    tool.description,
    tool.inputSchema?.properties ? tool.inputSchema : {},
    async (args: any) => {
      try {
        const result = await tool.handler(args);

        // If handler already returns MCP content format, pass through
        if (result && result.content && Array.isArray(result.content)) {
          return result;
        }

        // Otherwise wrap the result
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify({
                success: false,
                error: `Tool execution failed: ${errorMsg}`,
              }),
            },
          ],
          isError: true,
        };
      }
    }
  );
}

export default server;

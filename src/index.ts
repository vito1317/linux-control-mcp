#!/usr/bin/env node

/**
 * Linux Control MCP - Entry Point
 * Starts the MCP server with stdio transport
 */

import server from './server.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

/**
 * Start the server
 */
async function main() {
  const transport = new StdioServerTransport();

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.error('SIGINT received, shutting down gracefully');
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    console.error('SIGTERM received, shutting down gracefully');
    process.exit(0);
  });

  // Connect and run
  try {
    await server.connect(transport);
    console.error('Linux Control MCP server running on stdio transport');
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('Unexpected error:', error);
  process.exit(1);
});

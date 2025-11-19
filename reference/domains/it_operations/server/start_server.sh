#!/bin/bash
# IT Operations MCP Server startup script

# Set the default port
PORT=${1:-3000}

echo "Starting IT Operations MCP Server on port $PORT..."

# Start the server
uvicorn mcp_server:app --host 0.0.0.0 --port $PORT --reload

echo "Server stopped."
# IT Operations MCP Server

This is a standalone Model Context Protocol (MCP) server that provides system health monitoring tools for IT Operations. It can be deployed independently of the GCS Kernel system.

## Overview

The IT Operations MCP server provides tools for monitoring system health, similar to common Linux commands:

- `get_disk_usage`: Get disk usage information (like `df` command)
- `get_memory_usage`: Get memory usage information (like `free` command)
- `get_system_load`: Get system load averages
- `get_process_list`: Get a list of running processes

## Deployment

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Server

To start the server:

```bash
python mcp_server.py
```

Or using uvicorn directly:

```bash
uvicorn mcp_server:app --host 0.0.0.0 --port 3000
```

The server will start on port 3000 by default.

## Integration with GCS Kernel

The IT Operations domain in GCS Kernel is configured to connect to this MCP server. The domain metadata contains the server URL for automatic configuration.

## Protocol

This server implements the MCP specification (version 2025-06-18) using JSON-RPC 2.0 over Server-Sent Events (SSE).

## Security Considerations

- The server should only be deployed in trusted environments
- System monitoring commands may reveal sensitive information
- Consider using network segmentation and access controls
- The server should run with minimal privileges

## Architecture

The server is completely independent of the GCS Kernel and can be deployed:
- On the same machine as GCS Kernel
- On a separate management server
- In containerized environments
- On dedicated monitoring infrastructure
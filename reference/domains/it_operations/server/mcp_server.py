"""
IT Operations MCP Server Implementation

This module implements an MCP server for IT Operations system health monitoring.
It provides tools similar to 'df', 'free', and other system health commands.
"""

import json
import asyncio
import uuid
import subprocess
import shutil
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from datetime import datetime
import os


app = FastAPI(title="IT Operations MCP Server", version="1.0.0")


# Store for tool executions and sessions
executions_store = {}
session_store = {}


def create_json_rpc_response(request_id: str, result: Any) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }


def create_json_rpc_error(request_id: str, code: int, message: str) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }


def format_sse_event(data: str) -> str:
    """Format data as an SSE event."""
    return f"data: {data}\n\n"


def get_disk_usage(path: str = "/"):
    """Get disk usage information similar to the 'df' command."""
    try:
        # Use the 'df' command to get disk usage
        result = subprocess.run(
            ["df", "-h", path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error running df command: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error getting disk usage: {str(e)}"


def get_memory_usage(human_readable: bool = True):
    """Get memory usage information similar to the 'free' command."""
    try:
        # Use the 'free' command to get memory usage
        cmd = ["free", "-h"] if human_readable else ["free"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error running free command: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error getting memory usage: {str(e)}"


def get_system_load(duration: str = None):
    """Get system load averages."""
    try:
        # Read load average from /proc/loadavg
        with open("/proc/loadavg", "r") as f:
            load_data = f.read().strip().split()

        load_1min, load_5min, load_15min = load_data[0], load_data[1], load_data[2]

        if duration == "1min":
            return f"Load average (1 min): {load_1min}"
        elif duration == "5min":
            return f"Load average (5 min): {load_5min}"
        elif duration == "15min":
            return f"Load average (15 min): {load_15min}"
        else:
            return f"Load averages: 1 min: {load_1min}, 5 min: {load_5min}, 15 min: {load_15min}"
    except Exception as e:
        return f"Error getting system load: {str(e)}"


def get_process_list(process_name: str = None, limit: int = 20):
    """Get a list of running processes."""
    try:
        # Use the 'ps' command to get process list
        cmd = ["ps", "aux", "--sort=-%cpu", f"--no-headers"]
        if process_name:
            cmd.extend(["|", "grep", process_name])

        # Execute the command
        result = subprocess.run(
            " ".join(cmd),
            shell=True,  # Need shell=True to handle the pipe
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Limit the number of processes returned
            limited_lines = lines[:limit] if len(lines) > limit else lines
            return "\n".join(limited_lines)
        else:
            return f"Error running ps command: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error getting process list: {str(e)}"


async def process_initialize_request(params: Dict[str, Any], request_id: str):
    """Process an 'initialize' request according to MCP specification."""
    # Create a session ID
    session_id = str(uuid.uuid4())

    # Store session info
    session_info = {
        "sessionId": session_id,
        "created": datetime.now().isoformat()
    }
    session_store[session_id] = session_info

    # Prepare the InitializeResult
    initialize_result = {
        "serverInfo": {
            "name": "IT Operations MCP Server",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {
                "listChanged": False  # For this example, tools don't change dynamically
            }
        },
        "protocolVersion": "2025-06-18"
    }

    response = create_json_rpc_response(request_id, initialize_result)
    return response, session_id


async def process_list_tools_request(params: Dict[str, Any], request_id: str):
    """Process a 'tools/list' request."""
    tools = [
        {
            "name": "get_disk_usage",
            "description": "Get disk usage information similar to the 'df' command",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to check disk usage for, defaults to root filesystem"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_memory_usage",
            "description": "Get memory usage information similar to the 'free' command",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "human_readable": {
                        "type": "boolean",
                        "description": "Whether to show memory in human-readable format (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_system_load",
            "description": "Get system load averages",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "string",
                        "enum": ["1min", "5min", "15min"],
                        "description": "Load average duration to return (default: all)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_process_list",
            "description": "Get a list of running processes",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "Optional process name to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of processes to return (default: 20)"
                    }
                },
                "required": []
            }
        }
    ]

    result = {"tools": tools}
    response = create_json_rpc_response(request_id, result)
    return response, None


async def process_get_tool_request(params: Dict[str, Any], request_id: str):
    """Process a 'tools/get' request."""
    tool_name = params.get("name")

    if tool_name == "get_disk_usage":
        result = {
            "name": "get_disk_usage",
            "description": "Get disk usage information similar to the 'df' command",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to check disk usage for, defaults to root filesystem"
                    }
                },
                "required": []
            }
        }
    elif tool_name == "get_memory_usage":
        result = {
            "name": "get_memory_usage",
            "description": "Get memory usage information similar to the 'free' command",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "human_readable": {
                        "type": "boolean",
                        "description": "Whether to show memory in human-readable format (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        }
    elif tool_name == "get_system_load":
        result = {
            "name": "get_system_load",
            "description": "Get system load averages",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "string",
                        "enum": ["1min", "5min", "15min"],
                        "description": "Load average duration to return (default: all)"
                    }
                },
                "required": []
            }
        }
    elif tool_name == "get_process_list":
        result = {
            "name": "get_process_list",
            "description": "Get a list of running processes",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "Optional process name to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of processes to return (default: 20)"
                    }
                },
                "required": []
            }
        }
    else:
        error_message = f"Tool '{tool_name}' not found"
        response = create_json_rpc_error(request_id, -32602, error_message)
        return response, None

    response = create_json_rpc_response(request_id, result)
    return response, None


async def process_tools_call_request(params: Dict[str, Any], request_id: str):
    """Process a 'tools/call' request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    # Execute the appropriate tool
    if tool_name == "get_disk_usage":
        path = arguments.get("path", "/")
        result_data = get_disk_usage(path)
        result = {
            "toolName": tool_name,
            "output": result_data,
            "isError": False
        }
    elif tool_name == "get_memory_usage":
        human_readable = arguments.get("human_readable", True)
        result_data = get_memory_usage(human_readable=human_readable)
        result = {
            "toolName": tool_name,
            "output": result_data,
            "isError": False
        }
    elif tool_name == "get_system_load":
        duration = arguments.get("duration")
        result_data = get_system_load(duration)
        result = {
            "toolName": tool_name,
            "output": result_data,
            "isError": False
        }
    elif tool_name == "get_process_list":
        process_name = arguments.get("process_name")
        limit = arguments.get("limit", 20)
        result_data = get_process_list(process_name, limit)
        result = {
            "toolName": tool_name,
            "output": result_data,
            "isError": False
        }
    else:
        error_message = f"Tool '{tool_name}' not implemented"
        response = create_json_rpc_error(request_id, -32601, error_message)
        return response, None

    response = create_json_rpc_response(request_id, result)
    return response, None


async def handle_json_rpc_request(json_rpc_request: Dict[str, Any]):
    """Handle a JSON-RPC request based on its method."""
    method = json_rpc_request.get("method")
    request_id = json_rpc_request.get("id")  # This will be None for notifications
    params = json_rpc_request.get("params", {})

    # If it's a notification (no id), return empty response
    if request_id is None:
        return {}, None

    # Route the request to the appropriate handler
    try:
        if method == "initialize":
            return await process_initialize_request(params, request_id)
        elif method == "tools/list":
            return await process_list_tools_request(params, request_id)
        elif method == "tools/get":
            return await process_get_tool_request(params, request_id)
        elif method == "tools/call":
            return await process_tools_call_request(params, request_id)
        elif method == "initialized":
            # This is a notification, just return empty response
            return {}, None
        else:
            # Unknown method
            response = create_json_rpc_error(request_id, -32601, f"Method not found: {method}")
            return response, None
    except Exception as e:
        response = create_json_rpc_error(request_id, -32603, f"Internal error: {str(e)}")
        return response, None


@app.post("/")
async def mcp_endpoint(request: Request):
    """Main MCP endpoint that handles JSON-RPC requests and returns SSE responses."""
    # Get the body of the request
    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')

    try:
        json_rpc_request = json.loads(body_str)
    except json.JSONDecodeError:
        error_response = create_json_rpc_error(None, -32700, "Parse error")
        content = format_sse_event(json.dumps(error_response))
        return StreamingResponse(
            iter([content]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Important for SSE
            }
        )

    # Handle the JSON-RPC request
    response, session_id = await handle_json_rpc_request(json_rpc_request)

    # Create headers with session ID if it exists
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
        "X-Accel-Buffering": "no",  # Important for SSE
    }

    if session_id:
        headers["Mcp-Session-Id"] = session_id

    # Prepare the response content
    async def event_generator():
        if response:
            yield format_sse_event(json.dumps(response))

    # Return the response as an SSE stream
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers
    )


@app.get("/")
async def root_handler():
    """Root handler for basic HTTP requests."""
    return {
        "message": "This is an IT Operations MCP server providing system health monitoring tools",
        "protocol_version": "2025-06-18",
        "transport": "Streamable HTTP",
        "tools": [
            "get_disk_usage",
            "get_memory_usage",
            "get_system_load",
            "get_process_list"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info"
    )
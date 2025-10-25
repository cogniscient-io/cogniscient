# GCS Kernel - Generic Control System Kernel

The GCS Kernel is a minimal, operating-system-like kernel that provides core services for streaming AI agent orchestration. Inspired by Qwen Code's event loop and streaming response model, the kernel focuses on simplicity and modularity from the ground up.

## Architecture

The GCS Kernel follows a streaming, OS-like architecture with:
- A minimal kernel providing core services (streaming event loop, tool execution, and resource allocation)
- Additional functionalities implemented as services that run on top of the kernel
- Services interact with the kernel through well-defined interfaces for streaming tool execution and resource management
- User interfaces (CLI, Web UI) communicate with kernel via direct API for user interactions
- Internal service communication happens via MCP (Model Context Protocol) for tool execution and other kernel services
- The kernel enforces security boundaries and resource quotas for all services

## Core Components

### 1. Master Event Loop (Turn Processing)
- Initializes, runs, and shuts down the core event processing system
- Handles streaming AI responses and tool execution events in real-time
- Based on Qwen Code's Turn Processing architecture

### 2. Tool Execution Scheduler
- Manages complete tool lifecycle with 5 distinct states: Validating, Scheduled, Awaiting Approval, Executing, Completed
- Implements approval system with multiple modes (DEFAULT, PLAN, AUTO_EDIT, YOLO)
- Handles parameter validation against JSON schemas before execution

### 3. Tool Registry System
- Supports multiple discovery mechanisms: command-based and Model Context Protocol (MCP)-based
- Manages tool lifecycle: registration, validation, and availability
- Implements BaseTool interface with standardized contract for all tools

### 4. Resource Allocation Manager
- Allocates and enforces resource quotas (CPU, memory, I/O) for kernel operations and services
- Implements allocation and enforcement logic with configurable limits

### 5. Security Layer
- Enforces access control, authentication, and approval systems
- Implements token-based authentication with configurable permissions
- Provides kernel-mediated service communication through MCP interfaces

### 6. MCP Server and Client
- Server exposes kernel functions and tool execution capabilities via MCP interfaces
- Client connects to external tool servers, validates schemas and capabilities
- Ensures secure communication with external MCP services

## Getting Started

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the kernel in CLI mode:
```bash
python main.py --mode cli
```

3. Run the kernel as a server:
```bash
python main.py --mode server
```

## MCP Integration

The GCS Kernel implements MCP (Model Context Protocol) for standardized tool interaction:
- All internal tool and service communications use MCP interfaces
- User interfaces communicate with kernel via direct API (not MCP)
- Kernel MCP server enforces security, validation, and resource management for tool interactions
- Kernel MCP client connects to external tools/servers for additional capabilities

## Project Structure

```
gcs_kernel/                 # Core kernel functionality only
├── __init__.py
├── kernel.py               # Main GCS Kernel implementation
├── event_loop.py           # Master Event Loop (Turn Processing)
├── scheduler.py            # Tool execution scheduler
├── registry.py             # Tool registry system (kernel-level)
├── resource_manager.py     # Resource allocation manager
├── security.py             # Security layer
├── logger.py               # Event logging
└── mcp/
    ├── __init__.py
    ├── server.py           # MCP server to expose kernel services and tools
    └── client.py           # MCP client to connect to external tool services
services/                   # Services that run on top of the kernel
├── __init__.py
├── ai_orchestrator/        # AI orchestrator package
│   ├── __init__.py         # Package init
│   └── orchestrator_service.py # AI client orchestrator service
├── tool_discovery/         # Tool discovery services
│   ├── __init__.py
│   ├── command_discovery.py # Command-based tool discovery
│   └── mcp_discovery.py    # MCP-based tool discovery
└── example_service.py      # Example service implementation
ui/                         # User interface layer (separate from kernel and services)
├── __init__.py
├── cli/
│   ├── __init__.py
│   └── cli.py              # CLI interface
└── webui/                  # Web user interface (future implementation)
    ├── __init__.py
    └── app.py              # Web UI application
tests/                      # Unit test suite
├── test_kernel.py
├── test_event_loop.py
├── test_scheduler.py
├── test_registry.py
└── test_mcp.py
tests/integration/          # Integration test suite
└── test_kernel_llm_integration.py  # End-to-end kernel to LLM flow tests
requirements.txt            # Python dependencies
pyproject.toml              # Project configuration
main.py                     # Entry point
```

## Design Principles

- **Context is King**: All necessary documentation, examples, and caveats are included
- **Streaming First**: Built as a streaming-native kernel that processes AI responses and tool events in real-time
- **MCP Compliance**: All internal tool and service communications use MCP interfaces
- **Security First**: Kernel enforces security boundaries between services; no direct service-to-service communication without kernel mediation
- **Modular Extensibility**: Clear service boundaries for safe extension
- **Observability**: Comprehensive logging and monitoring of system state

## Success Metrics

- Tool registry successfully registers and discovers tools via both command-based and MCP-based mechanisms
- MCP communication between services works reliably for 100% of registered services
- Kernel resource overhead stays under 20% of system resources
- Tool loading and execution time stays under 100ms
- System can run for 7 days without restart under normal load
- Sub-second response times for streaming AI interactions
- Successful execution of tool lifecycle: validation, approval (when required), execution, and result return
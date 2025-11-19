# GCS Kernel - Generic Control System Kernel

The GCS Kernel is a minimal, operating-system-like kernel that provides core services for streaming AI agent orchestration. Inspired by Qwen Code's event loop and streaming response model, the kernel focuses on simplicity and modularity from the ground up.

## Getting Started

1. Install the package in development mode:
```bash
pip install -e .
```

2. Run the GCS Kernel CLI:
```bash
gcs
```

3. Or run in server mode:
```bash
gcs --mode server
```

4. For help with available options:
```bash
gcs --help
```

5. Alternative method (if not installed as a package):
```bash
pip install -r requirements.txt
python main.py --mode cli
```

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

## MCP Integration

The GCS Kernel implements MCP (Model Context Protocol) for standardized tool interaction:
- All internal tool and service communications use MCP interfaces
- User interfaces communicate with kernel via direct API (not MCP)
- Kernel MCP server enforces security, validation, and resource management for tool interactions
- Kernel MCP client connects to external tools/servers for additional capabilities

## Project Structure

```
├── pyproject.toml          # Project configuration and package metadata
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── .env                   # Environment variables
├── .env.example           # Example environment variables
├── gcs_kernel/            # Core kernel functionality
│   ├── __init__.py
│   ├── __main__.py
│   ├── kernel.py          # Main GCS Kernel implementation
│   ├── event_loop.py      # Master Event Loop (Turn Processing)
│   ├── registry.py        # Tool registry system (kernel-level)
│   ├── resource_manager.py # Resource allocation manager
│   ├── security.py        # Security layer
│   ├── logger.py          # Event logging
│   ├── models.py          # Data models
│   ├── tool_call_model.py # Tool call data model
│   ├── tool_execution_manager.py # Tool execution management
│   └── mcp/              # Model Context Protocol components
│   │   ├── __init__.py
│   │   ├── server.py     # MCP server to expose kernel services and tools
│   │   ├── client.py     # MCP client to connect to external tool services
│   │   ├── client_manager.py # MCP client manager
│   │   └── server_registry.py # MCP server registry
│   └── tools/            # Built-in tools for the kernel
│       ├── __init__.py
│       ├── file_operations.py # File operation tools
│       ├── mcp_tools.py  # MCP-related tools
│       ├── shell_command.py # Shell command tools
│       └── system_tools.py # System utilities
├── services/              # Services that run on top of the kernel
│   ├── __init__.py
│   ├── ai_orchestrator/   # AI orchestrator service
│   │   ├── __init__.py
│   │   ├── orchestrator_service.py # AI client orchestrator service
│   │   ├── prompts.json  # Prompt templates
│   │   ├── system_context_builder.py # System context builder
│   │   └── turn_manager.py # Turn management
│   ├── adaptive_loop/     # Adaptive Loop service
│   │   ├── adaptive_loop_service.py # Adaptive Loop implementation
│   │   └── __init__.py
│   ├── llm_provider/      # LLM provider service
│   │   ├── __init__.py
│   │   ├── content_generator.py # Content generation logic
│   │   ├── pipeline.py   # Processing pipeline
│   │   ├── base_converter.py # Base converter
│   │   ├── base_generator.py # Base generator
│   │   ├── interfaces.py # Interfaces
│   │   ├── test_mocks.py # Test mocks
│   │   └── providers/    # LLM provider implementations
│   │       ├── __init__.py
│   │       ├── base_provider.py # Base provider
│   │       ├── mock_provider.py # Mock provider
│   │       ├── openai_provider.py # OpenAI provider
│   │       ├── openai_converter.py # OpenAI converter
│   │       └── provider_factory.py # Provider factory
│   ├── tool_discovery/    # Tool discovery services
│   │   ├── __init__.py
│   │   ├── command_discovery.py # Command-based tool discovery
│   │   └── mcp_discovery.py # MCP-based tool discovery
│   ├── example_service.py # Example service implementation
│   └── example_mcp_server.py # Example MCP server
├── ui/                    # User interface layer
│   ├── __init__.py
│   ├── cli/              # Command-line interface
│   │   ├── __init__.py
│   │   ├── cli.py        # CLI interface
│   │   └── demo_streaming.py # Demo streaming functionality
│   ├── common/           # Common UI components
│   │   ├── __init__.py
│   │   ├── base_ui.py    # Base UI class
│   │   ├── cli_ui.py     # CLI UI implementation
│   │   └── kernel_api.py # Kernel API client
│   └── webui/            # Web user interface
│       ├── __init__.py
│       └── app.py        # Web UI application
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
├── common/                # Common utilities
├── custom_runtime/        # Custom runtime components
└── runtime_data/          # Runtime data directory
```

## Design Principles

- **Context is King**: All necessary documentation, examples, and caveats are included
- **Streaming First**: Built as a streaming-native kernel that processes AI responses and tool events in real-time
- **MCP Compliance**: All internal tool and service communications use MCP interfaces
- **Security First**: Kernel enforces security boundaries between services; no direct service-to-service communication without kernel mediation
- **Modular Extensibility**: Clear service boundaries for safe extension
- **Observability**: Comprehensive logging and monitoring of system state

## TODOs

- There is no history.  Each prompt is independent at the moment.
- Need to work on "stacking."  A GCS instance needs to behave as an MCP Server for another GCS instance.  Think orchestration layer on top of several smaller control systems
- Still not happy with the system context.  LLM tool calling is not consistent enough.
- Need to add mutation logging/auditability for the positive feedback scenarios.
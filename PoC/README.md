# Cogniscient - Generic Control System Engine

Cogniscient is a generic control system engine for managing AI agents and services with LLM integration. This project demonstrates an LLM-enhanced orchestration system that can adaptively retry failed tasks and adjust parameters based on LLM evaluations. It also includes a chat interface that allows users to check website status through natural language commands.

## Features

- **Adaptive Orchestration**: The system uses an LLM to evaluate the results of agent executions and decide on the next steps.
- **Retry Logic**: If an agent fails, the system can retry the task with different parameters suggested by the LLM.
- **Parameter Adaptation**: The system can adjust agent parameters based on LLM suggestions to improve the chances of success.
- **Proper Error Handling**: The system correctly handles DNS lookup failures for non-existent domains.
- **Robust LLM Response Parsing**: The system can handle various formats of LLM responses and extract structured data.
- **Website Checking via Chat Interface**: Users can check website status through natural language commands like "check website <url>" in the chat interface.
- **Intelligent Error Diagnosis**: When website checks fail, the system provides intelligent diagnosis and resolution suggestions.

## Prerequisites

- Python 3.10 or higher
- Ollama running on `http://<ip_addr>:11434` (or update the settings in `.env` and `src/config/settings.py`)
- Qwen3:8b model installed in Ollama (or update the model name in settings)
- Any model should work, really, but I'm testing locally using this smaller model.

## Installation

### As a Package

You can install Cogniscient as a Python package:

```bash
pip install cogniscient
```

After installation, you can use it in your Python code:

```python
from cogniscient import GCSRuntime

# Initialize the runtime
gcs = GCSRuntime()
gcs.load_all_agents()

# Use the system
result = gcs.run_agent("SampleAgentA", "perform_dns_lookup")
```

You can also use the CLI:

```bash
# Show available commands
cogniscient --help

# Run the system
cogniscient run

# List configurations
cogniscient list-configs

# Load a specific configuration
cogniscient load-config --config-name my-config
```

### For Development

1. Clone the repository and install in development mode:
   ```bash
   git clone <repository-url>
   cd PoC
   pip install -e .
   # Or with development dependencies
   pip install -e ".[dev]"
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   Or install the packages directly:
   ```bash
   pip install litellm pydantic-settings pytest pytest-asyncio uvicorn fastapi dnspython
   ```

3. Make sure Ollama is running with the Qwen3:8b model:
   ```bash
   ollama run qwen3:8b
   ```

## Configuration

The system can be configured through:
1. Environment variables in the `.env` file
2. Direct modification of `src/config/settings.py`

Key configuration options:
- `LLM_MODEL`: The model to use (default: `ollama_chat/qwen3:8b`)
- `LLM_BASE_URL`: The Ollama server URL (default: `http://<ip_addr>:11434`)
- `LLM_API_KEY`: API key if required (default: `ollama`)

## How It Works

1. The `demo_llm_orchestration.py` script initializes the UCS runtime and loads the agents.
2. It then demonstrates the adaptive orchestration loop:
   - An agent is executed.
   - The LLM evaluates the result and decides whether to retry, adjust parameters, or consider the task successful.
   - If a retry is needed, the LLM can suggest new parameters to use for the retry.
3. The script also demonstrates a failure and retry scenario using a domain that is expected to fail (`test.cogniscient.io`).

## Key Components

- **UCSRuntime**: Manages the loading and execution of agents, and maintains their configurations.
- **LLMOrchestrator**: Orchestrates agent executions and uses an LLM to evaluate results and decide on next steps.
- **SampleAgentA**: A sample agent that performs DNS lookups using a configurable DNS server.
- **SampleAgentB**: Another sample agent that performs website checks.

## Orchestration Flow

The orchestration flow has two main modes of operation:

1. **Direct Agent Orchestration**: Using the `orchestrate_agent` method for specific agent execution with LLM evaluation
2. **Chat-based Orchestration**: Using the `process_user_request` method for natural language interaction

### Direct Agent Orchestration Flow

```mermaid
graph TD
    A[Start] --> B[Initialize UCS Runtime]
    B --> C[Load Agents]
    C --> D[Execute Agent Method]
    D --> E[LLM Evaluates Result]
    E --> F{Decision?}
    F -->|Success| G[Task Completed]
    F -->|Retry| H[LLM Suggests Parameters]
    H --> I[Adapt Parameters]
    I --> D
    F -->|Failure| J[Task Failed]
    J --> K[End]
    G --> K
```

### Chat-based Orchestration Flow

```mermaid
graph TD
    A[User Input] --> B[Process Request]
    B --> C[LLM Determines Tool Call]
    C --> D{Tool Call?}
    D -->|Yes| E[Execute Agent Method]
    E --> F[Add Result to Context]
    F --> G[LLM Analyzes Results]
    G --> H{More Investigation?}
    H -->|Yes| I[LLM Determines Next Tool Call]
    I --> E
    H -->|No| J[Generate User Response]
    D -->|No| J
    J --> K[Return Response]
```

### Key Changes in Orchestration Logic

1. **Enhanced LLM Response Parsing**: The system now has robust JSON parsing capabilities that can extract structured data even when the LLM includes additional text around the JSON.

2. **Chat-based Agent Selection**: The chat interface allows users to interact with the system through natural language. The LLM determines which agents to call based on the user's request.

3. **Intelligent Error Diagnosis**: When website checks fail, the system automatically performs DNS lookups to determine if the domain exists, providing more detailed error information.

4. **Preventive Loop Protection**: The system tracks tool calls to prevent infinite loops by avoiding duplicate tool calls.

5. **Adaptive Investigation**: The system can make up to two tool calls to investigate an issue thoroughly before providing a final response to the user.

6. **Structured Agent Responses**: Agents now return structured responses with detailed status information, making it easier for the LLM to evaluate results.

## Running the Demo

To run the demo, execute the following command:

```bash
python3 demo_llm_orchestration.py
```

This will show the adaptive orchestration in action, including:
1. A successful DNS lookup for a valid domain
2. A failed DNS lookup for a non-existent domain (`test.cogniscient.io`) with retry attempts
3. Parameter adaptation demonstration
4. Chat interface demonstration
5. Website checking functionality demonstration

The demo showcases how the system can handle both successful and failed agent executions, and how it uses LLM evaluations to make decisions about retrying tasks or adjusting parameters. The system correctly identifies when a task cannot be completed (like a non-existent domain) and stops retrying after a few attempts.

## Website Checking via Chat Interface

Users can check website status through natural language commands in the chat interface:

1. **Command Format**: Users can type commands like "check website <url>", "test site <url>", or "verify url <url>"
2. **Successful Checks**: For accessible websites, the system responds with status information
3. **Error Diagnosis**: For inaccessible websites, the system provides intelligent diagnosis and resolution suggestions
4. **Integration**: The feature integrates seamlessly with the existing chat interface and LLM orchestrator

Example commands:
- `check website https://example.com`
- `test site http://google.com`
- `verify url https://github.com`

The system uses SampleAgentB to perform the actual website checks and the LLM orchestrator to provide intelligent analysis of results.

## Packaging

The project is configured as a Python package that can be built and distributed:

```bash
# Build the package
pip install build
python -m build

# The package includes:
# - The core GCSRuntime class
# - Agent management utilities
# - Configuration services
# - CLI interface
```

For more details on the release process, see [RELEASE.md](RELEASE.md).

## Troubleshooting

If you encounter issues with the LLM service:

1. **Model Name Format**: Ensure the model name uses the correct format for Ollama (`ollama_chat/model_name`)
2. **Base URL**: Make sure the base URL doesn't have `/v1` appended for Ollama
3. **Environment Variables**: If you have environment variables set, they may override the settings in `.env`. You can unset them with:
   ```bash
   unset LLM_MODEL LLM_BASE_URL
   ```
4. **Ollama Connection**: Ensure Ollama is running and accessible at the specified URL
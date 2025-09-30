# Sample External Plugin: Website Host Manager

This plugin implements an external agent that runs on a website hosting machine. It monitors system resources and manages the website hosting software via an MCP (Model Context Protocol) server.

## Features

- Monitors CPU, memory, network, and disk usage
- Tracks the status of the hosted software process
- Can restart the hosted software if it becomes unresponsive
- Exposes these capabilities via MCP protocol as an MCP server
- Configurable thresholds and intervals

## Configuration

The agent is configured via `config.json`:

- `hosted_software_process_name`: Name of the process to monitor (default: nginx)
- `restart_threshold`: Time in seconds after which to consider the software hung (default: 60)

## Usage

To run the agent:

```bash
cd /home/tsai/src/cogniscient/PoC
python -m plugins.sample_external.agents.website_host_manager
```

## Architecture

The agent implements the following capabilities as MCP server tools:

1. **get_system_metrics**: Collects various system metrics using psutil
2. **check_hosted_software_status**: Checks if the hosted software process is running
3. **restart_hosted_software**: Restarts the hosted software if it's unresponsive

## Integration with MCP

The agent functions as an MCP server that:
- Exposes its tools to MCP clients (like the Cogniscient system)
- Waits for tool calls from the orchestrator
- Responds with the results of the operations

The MCP client (Cogniscient system) can discover and call these tools automatically based on the needs of the system.

## Security Considerations

- The agent has the ability to restart system processes
- Ensure proper access controls are in place
- Monitor the agent's activities in production
- Validate and sanitize any parameters sent through MCP tool calls
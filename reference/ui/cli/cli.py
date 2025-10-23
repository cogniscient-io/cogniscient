"""
CLI Interface implementation for the GCS Kernel.

This module implements the CLIInterface class which provides
a simple command-line interface to control the kernel and manage tool execution.
"""

import asyncio
from typing import Any, Optional
from gcs_kernel.mcp.client import MCPClient


class CLIInterface:
    """
    CLI Interface that provides commands to control kernel and manage tool execution.
    Communicates with kernel MCP server via MCP client for tool execution.
    """
    
    def __init__(self, kernel_api_client: Any, mcp_client: Optional[MCPClient] = None):
        """
        Initialize the CLI interface.
        
        Args:
            kernel_api_client: Direct API client for user interactions with kernel
            mcp_client: Optional MCP client for specific kernel services when needed
        """
        # Accept direct API client for user interactions with kernel
        self.kernel_api_client = kernel_api_client
        # Accept optional MCP client for specific kernel services when needed
        self.mcp_client = mcp_client

    def run(self):
        """
        Run the CLI interface.
        """
        print("GCS Kernel CLI - Type 'help' for commands or 'exit' to quit")
        
        try:
            while True:
                try:
                    user_input = input("gcs> ").strip()
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    elif user_input.lower() == 'help':
                        self.show_help()
                    else:
                        # Process user input using direct API to kernel
                        result = self.process_user_input(user_input)
                        print(result)
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
        except Exception as e:
            print(f"Error in CLI: {e}")

    def show_help(self):
        """
        Show help information for available commands.
        """
        help_text = """
GCS Kernel CLI Commands:
  help                    - Show this help message
  status                  - Get kernel status
  list-tools              - List available tools
  run-tool <name> [args]  - Execute a tool with arguments
  ai <prompt>             - Send a prompt to the AI orchestrator
  exit/quit               - Exit the CLI

Examples:
  gcs> status
  gcs> list-tools
  gcs> run-tool read_file path=README.md
  gcs> ai What files are in the current directory?
        """
        print(help_text)

    def process_user_input(self, user_input: str):
        """
        Process user input using direct API to kernel.
        
        Args:
            user_input: The raw user input string
            
        Returns:
            The result of processing the user input
        """
        # Check if this is a special command or a prompt for AI
        if user_input.startswith('!'):
            # This is a system command
            command = user_input[1:]  # Remove '!' prefix
            return self.process_command(command)
        elif user_input.startswith('ai '):
            # This is a user prompt to send to AI orchestrator
            prompt = user_input[3:]  # Remove 'ai ' prefix
            return self.kernel_api_client.send_user_prompt(prompt)
        else:
            # This is a user prompt to send to AI orchestrator
            return self.kernel_api_client.send_user_prompt(user_input)

    def process_command(self, command: str):
        """
        Process a CLI command using direct API to kernel.
        
        Args:
            command: The command string to process
            
        Returns:
            The result of processing the command
        """
        # Parse the command and call appropriate kernel functions via direct API
        parts = command.split()
        if not parts:
            return "No command provided"
            
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == 'status':
            # Get kernel status via direct API
            return self.kernel_api_client.get_kernel_status()
        elif cmd == 'list-tools':
            # List available tools via direct API
            return self.kernel_api_client.list_registered_tools()
        elif cmd == 'run-tool':
            # Execute a tool via direct API (which may use MCP internally)
            if len(args) >= 1:
                tool_name = args[0]
                tool_args = args[1:]
                # Parse arguments as key=value pairs
                params = {}
                for arg in tool_args:
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        params[key] = value
                    else:
                        params[arg] = True  # For flag-like arguments
                
                if self.mcp_client:
                    # Use MCP client to submit tool execution to kernel
                    return asyncio.run(self.mcp_client.submit_tool_execution(tool_name, params))
                else:
                    return "MCP client not available"
        elif cmd == 'list-executions':
            # List recent tool executions
            if self.mcp_client:
                return asyncio.run(self.mcp_client.list_executions())
            else:
                return "MCP client not available"
        else:
            return f"Unknown command: {cmd}. Type 'help' for available commands."
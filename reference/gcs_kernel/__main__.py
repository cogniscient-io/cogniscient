"""
Entry point for the GCS Kernel when run as a module.

This module provides the main entry point for starting the GCS Kernel
and initializing all its components when run as `python -m gcs_kernel`.
"""
import asyncio
import argparse
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.models import MCPConfig
from ui.cli.cli import CLIInterface


async def main():
    """Main entry point for the GCS Kernel."""
    parser = argparse.ArgumentParser(description="GCS Kernel - Generic Control System Kernel")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--mode", type=str, choices=["cli", "server", "api"], 
                        default="cli", help="Operation mode")
    args = parser.parse_args()
    
    # Initialize the kernel
    kernel = GCSKernel()
    
    try:
        # Start the kernel
        kernel_task = asyncio.create_task(kernel.run())
        
        if args.mode == "cli":
            # Run CLI interface
            mcp_config = MCPConfig(server_url="http://localhost:8000")
            from gcs_kernel.mcp.client import MCPClient
            from gcs_kernel.mcp.client_manager import MCPClientManager
            import hashlib
            
            # Create client manager and connect to kernel
            client_manager = MCPClientManager(mcp_config)
            await client_manager.initialize()
            success = await client_manager.connect_to_server("http://localhost:8000", server_name="local_kernel")
            if not success:
                print("Failed to connect to kernel via MCP")
                return
            
            # Get the client for the kernel
            server_id = next(iter(client_manager.clients.keys()))
            client_data = client_manager.clients[server_id]
            mcp_client = client_data['client']
            
            # Create a simple API client for CLI that communicates with the kernel via MCP
            # The kernel handles everything else including LLM interaction
            import threading
            import queue
            
            class MCPKernelAPIClient:
                def __init__(self, mcp_client, kernel):
                    self.mcp_client = mcp_client  # Use the MCP client to communicate with kernel
                    self.kernel = kernel
                
                def get_kernel_status(self):
                    return f"Kernel running: {self.kernel.is_running()}"
                
                def list_registered_tools(self):
                    if self.kernel.registry:
                        tools = self.kernel.registry.get_all_tools()
                        return list(tools.keys())
                    return []
                
                def send_user_prompt(self, prompt):
                    # In a real system, this would send the prompt to the kernel via MCP
                    # and wait for the response, but for now we'll return a placeholder
                    # until the kernel properly implements the AI interface via MCP
                    return f"Processing prompt: {prompt}"
                
                def stream_user_prompt(self, prompt):
                    # In a real streaming implementation, this would establish a streaming
                    # connection via MCP and yield chunks as they arrive from the kernel
                    # For now, return a single chunk as if it were streamed
                    yield f"Processing prompt: {prompt}"
            
            api_client = MCPKernelAPIClient(mcp_client, kernel)
            cli = CLIInterface(api_client, mcp_client)
            cli.run()
        elif args.mode == "server":
            # Just run the kernel as a server
            print("GCS Kernel running in server mode...")
            await kernel_task
        elif args.mode == "api":
            # In API mode, we might expose a REST API
            print("GCS Kernel API mode not implemented yet")
            await kernel_task
    
    except KeyboardInterrupt:
        print("\nShutting down GCS Kernel...")
    finally:
        await kernel.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
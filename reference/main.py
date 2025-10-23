"""
Entry point for the GCS Kernel.

This module provides the main entry point for starting the GCS Kernel
and initializing all its components.
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
            mcp_client = MCPClient(mcp_config)
            await mcp_client.initialize()
            
            # Create a simple API client for CLI (in a real system this would be a proper API client)
            class SimpleKernelAPIClient:
                def get_kernel_status(self):
                    return f"Kernel running: {kernel.is_running()}"
                
                def list_registered_tools(self):
                    if kernel.registry:
                        tools = kernel.registry.get_all_tools()
                        return list(tools.keys())
                    return []
                
                def send_user_prompt(self, prompt):
                    # In a real system, this would send the prompt to the AI orchestrator
                    return f"Processing prompt: {prompt}"
            
            api_client = SimpleKernelAPIClient()
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
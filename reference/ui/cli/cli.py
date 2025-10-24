#!/usr/bin/env python3
"""
CLI Interface implementation for the GCS Kernel.

This module implements the CLI using new common UI components with proper async resource management.
"""

import asyncio
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.models import MCPConfig
from gcs_kernel.mcp.client import MCPClient
from ui.common.kernel_api import KernelAPIClient
from ui.common.cli_ui import CLIUI


def main():
    """Main entry point for the GCS CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GCS Kernel - Generic Control System Kernel")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--mode", type=str, choices=["cli", "server", "api"], 
                        default="cli", help="Operation mode")
    args = parser.parse_args()
    
    # Initialize the kernel
    kernel = GCSKernel()
    
    async def _async_main():
        kernel_task = None
        try:
            # Start the kernel
            kernel_task = asyncio.create_task(kernel.run())
            
            if args.mode == "cli":
                # Wait for kernel to initialize before starting CLI
                max_wait = 10  # seconds to wait for kernel initialization
                wait_interval = 0.1
                elapsed = 0
                while elapsed < max_wait:
                    # Check if kernel has completed full initialization
                    if getattr(kernel, '_fully_initialized', False):
                        break
                    await asyncio.sleep(wait_interval)  # Use async sleep to allow other tasks to run
                    elapsed += wait_interval
                
                if elapsed >= max_wait:
                    print(f"Warning: Kernel initialization took longer than {max_wait} seconds, proceeding anyway...")
                
                # Initialize MCP client for kernel communication
                mcp_config = MCPConfig(server_url="http://localhost:8000")
                mcp_client = MCPClient(mcp_config)
                await mcp_client.initialize()
                
                # Create the new clean kernel API client
                kernel_api_client = KernelAPIClient(kernel)
                
                # Create the new CLI UI with proper async resource management
                cli_ui = CLIUI(kernel_api_client)
                
                # Run the interactive CLI loop
                await cli_ui._interactive_loop()
                
            elif args.mode == "server":
                # Just run the kernel as a server
                print("GCS Kernel running in server mode...")
                await kernel_task
            elif args.mode == "api":
                # In API mode, we might expose a REST API
                print("GCS Kernel API mode not implemented yet")
                await kernel_task
        
        except KeyboardInterrupt:
            print("\nReceived interrupt signal...")
        finally:
            # Cancel the kernel task and wait for it to finish
            if kernel_task and not kernel_task.done():
                kernel_task.cancel()
                try:
                    await kernel_task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling the task
            
            # Now shutdown the kernel
            await kernel.shutdown()
    
    # Actually run the async function
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
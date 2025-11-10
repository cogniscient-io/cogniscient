#!/usr/bin/env python3
"""
Demo script to showcase the streaming AI functionality in the CLI.

This script demonstrates how the CLI now connects to the kernel's AI orchestrator
and streams responses in real-time.
"""

import asyncio
import sys
import os
import hashlib

# Add the project root to the path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gcs_kernel.kernel import GCSKernel
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.mcp.client_manager import MCPClientManager
from gcs_kernel.models import MCPConfig
from ui.cli.cli import CLIInterface


async def demo_streaming():
    """Demonstrate the streaming functionality."""
    print("Starting GCS Kernel with streaming AI support...")
    
    # Initialize the kernel
    kernel = GCSKernel()
    
    # Start the kernel
    kernel_task = asyncio.create_task(kernel.run())
    
    try:
        # Wait a moment for the kernel to initialize
        await asyncio.sleep(0.5)
        
        # Create MCP client manager
        mcp_config = MCPConfig(server_url="http://localhost:8000")
        from gcs_kernel.mcp.client_manager import MCPClientManager
        client_manager = MCPClientManager(mcp_config)
        await client_manager.initialize()
        
        # Connect to the kernel
        success = await client_manager.connect_to_server("http://localhost:8000", server_name="local_kernel")
        if not success:
            print("Failed to connect to kernel via MCP")
            return
        
        # Get the client for the kernel
        server_id = next(iter(client_manager.clients.keys()))
        client_data = client_manager.clients[server_id]
        mcp_client = client_data['client']
        
        # Create API client that connects to kernel
        class KernelAPIClient:
            def __init__(self, kernel):
                self.kernel = kernel

            def get_kernel_status(self):
                return f"Kernel running: {self.kernel.is_running()}"

            def list_registered_tools(self):
                if self.kernel.registry:
                    tools = self.kernel.registry.get_all_tools()
                    return list(tools.keys())
                return []

            def send_user_prompt(self, prompt):
                import asyncio
                import threading
                result_container = [None]
                exception_container = [None]

                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result_container[0] = asyncio.run(
                            self.kernel.submit_prompt(prompt)
                        )
                    except Exception as e:
                        exception_container[0] = e
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception_container[0]:
                    raise exception_container[0]
                return result_container[0]

            def stream_user_prompt(self, prompt):
                import threading
                import queue
                stop_event = threading.Event()
                chunk_queue = queue.Queue()

                def run_streaming_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)

                    async def stream_async():
                        try:
                            async for chunk in self.kernel.stream_prompt(prompt):
                                chunk_queue.put(('chunk', chunk))
                            chunk_queue.put(('done', None))
                        except Exception as e:
                            chunk_queue.put(('error', e))

                    try:
                        new_loop.run_until_complete(stream_async())
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_streaming_in_thread)
                thread.start()

                while True:
                    chunk_type, chunk_data = chunk_queue.get()
                    if chunk_type == 'done':
                        break
                    elif chunk_type == 'error':
                        raise chunk_data
                    yield chunk_data

                thread.join()

        api_client = KernelAPIClient(kernel)
        cli = CLIInterface(api_client, mcp_client)
        
        print("\n" + "="*50)
        print("DEMO: Streaming AI Responses")
        print("="*50)
        
        # Example prompts to test streaming
        test_prompts = [
            "Hello, how are you?",
            "What is the capital of France?",
            "Count from 1 to 5"
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\nTest {i}: {prompt}")
            print("-" * 30)
            
            # Process the prompt using the CLI's method which handles streaming
            result = cli.process_user_input(prompt)
            print(f"\nFinal result: {result}")
        
        # Test with the 'ai' command prefix as well
        print(f"\nTest AI command: ai What is streaming AI?")
        print("-" * 30)
        result = cli.process_user_input("ai What is streaming AI?")
        print(f"\nFinal result: {result}")
        
        print("\nStreaming demo completed successfully!")
        
    finally:
        # Cancel the kernel task and shutdown
        kernel_task.cancel()
        try:
            await kernel_task
        except asyncio.CancelledError:
            pass
        
        await kernel.shutdown()


if __name__ == "__main__":
    print("GCS Kernel Streaming AI Demo")
    print("This demo shows how the CLI is now wired up to stream AI responses from the kernel.")
    
    try:
        asyncio.run(demo_streaming())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
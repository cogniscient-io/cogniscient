"""
CLI-specific UI implementation using the common base UI.
This implementation properly handles async streaming without problematic threading patterns.
"""

import asyncio
from typing import AsyncGenerator
from .base_ui import BaseUI, KernelAPIProtocol, StreamingHandler


class CLIUI(BaseUI):
    """CLI-specific UI implementation with proper async resource management."""
    
    def __init__(self, kernel_api: KernelAPIProtocol):
        super().__init__(kernel_api)
        self.streaming_handler = StreamingHandler()
    
    async def display_streaming_response(self, prompt: str) -> str:
        """Display a streaming response from the kernel with proper async handling."""
        def print_chunk(chunk: str):
            print(chunk, end='', flush=True)
        
        try:
            stream_generator = self.kernel_api.stream_user_prompt(prompt)
            response = await self.streaming_handler.handle_streaming_with_callback(
                stream_generator,
                print_chunk
            )
            print()  # New line after streaming completes
            return response
        except Exception as e:
            error_msg = f"Error during streaming: {str(e)}"
            print(f"\n{error_msg}")
            return error_msg
    
    async def display_response(self, prompt: str) -> str:
        """Display a non-streaming response from the kernel."""
        try:
            response = await self.kernel_api.send_user_prompt(prompt)
            print(response)
            return response
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            return error_msg
    
    def run_interactive_loop(self):
        """Run the interactive CLI loop."""
        # Since we're already in an event loop context, we don't need to call asyncio.run()
        # The caller should await _interactive_loop() directly
        raise RuntimeError("run_interactive_loop should not be called directly. Use await _interactive_loop() instead.")
    
    async def _interactive_loop(self):
        """Internal async interactive loop."""
        print("GCS Kernel CLI - Type 'help' for commands or 'exit' to quit")
        
        while True:
            try:
                user_input = await self._get_user_input()
                if user_input.lower() in ['exit', 'quit']:
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                elif user_input.lower().startswith('ai '):
                    # Process AI command with streaming
                    prompt = user_input[3:]  # Remove 'ai ' prefix
                    await self.display_streaming_response(prompt)
                else:
                    # Default to AI processing if not a recognized command
                    await self.display_streaming_response(user_input)
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error processing input: {e}")
    
    async def _get_user_input(self) -> str:
        """Get user input asynchronously."""
        # Use a coroutine to get input without blocking the event loop
        loop = asyncio.get_event_loop()
        user_input = await loop.run_in_executor(None, input, "gcs> ")
        return user_input.strip()
    
    def show_help(self):
        """Show help information."""
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
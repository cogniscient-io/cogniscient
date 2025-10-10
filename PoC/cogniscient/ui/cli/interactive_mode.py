"""
Interactive mode implementation for Cogniscient CLI.

This module provides the REPL-style interactive interface.
"""
import os
import asyncio
from typing import Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.llm_orchestrator.chat_interface import ChatInterface
from cogniscient.engine.llm_orchestrator.llm_orchestrator import LLMOrchestrator
from .session_manager import SessionManager
from cogniscient.auth.oauth_manager import OAuthManager
from cogniscient.auth.token_manager import TokenManager
from cogniscient.engine.config.settings import settings

class InteractiveCLI:
    """
    Main class for the interactive CLI interface.
    """
    
    def __init__(self, gcs_runtime: GCSRuntime):
        """
        Initialize the interactive CLI.
        
        Args:
            gcs_runtime: GCS runtime instance
        """
        self.gcs_runtime = gcs_runtime
        self.session_manager = SessionManager(gcs_runtime)
        
        # Initialize orchestrator and chat interface for LLM interactions
        self.orchestrator = LLMOrchestrator(gcs_runtime)
        self.chat_interface = ChatInterface(self.orchestrator)
        
        # Register orchestrator and chat interface with the kernel
        gcs_runtime.set_llm_orchestrator(self.orchestrator)
        gcs_runtime.register_chat_interface(self.chat_interface)
        
        # Create a prompt session with history
        history_file = os.path.expanduser("~/.cogniscient_history")
        self.session = PromptSession(history=FileHistory(history_file))
        
        # Define command completions
        self.completer = WordCompleter([
            'help', 'exit', 'quit', 'status', 
            'list-configs', 'list-agents', 'run-agent',
            'auth', 'auth-status', 'switch-provider', 'list-providers'
        ])
    
    def start_session(self):
        """
        Start the interactive session.
        This is now just an interface to the kernel - the actual control loop runs in the kernel.
        """
        print("Cogniscient Interactive CLI v0.1.0")
        
        # Show current system status
        agents = list(self.gcs_runtime.agents.keys())
        print("System status: Ready")
        print(f"Active agents: {', '.join(agents) if agents else 'None'}")
        print("Type 'help' for available commands or just start typing.\n")
        
        # Add special session start message to history
        self.session_manager.add_interaction("SYSTEM", "Interactive session started")
        
        # Inform the user that the kernel is running its control loop
        print("Kernel control loop is running in the background. CLI provides interface to interact with it.\n")
        
        # Register this CLI as an input/output handler with the kernel
        self.gcs_runtime.kernel.set_input_handler(self._handle_input)
        self.gcs_runtime.kernel.set_output_handler(self._handle_output)
        
        try:
            # Start the kernel's main control loop if it hasn't been started already
            if not hasattr(self.gcs_runtime, 'kernel_started') or not self.gcs_runtime.kernel_started:
                self.gcs_runtime.start_kernel_loop()
                self.gcs_runtime.kernel_started = True
            
            # Main CLI input loop - this handles just the user input/output
            while True:
                try:
                    # Get user input with custom prompt
                    user_input = self.session.prompt('Cogniscient> ', completer=self.completer)
                    
                    # Process the input - this will go through the kernel
                    response = self._handle_input(user_input)
                    
                    # Output the response
                    self._handle_output(response)
                    
                    # Add interaction to history
                    self.session_manager.add_interaction(user_input, response)
                    
                    # Check if user wants to exit
                    if user_input.lower().strip() in ['exit', 'quit', 'bye']:
                        break
                        
                except KeyboardInterrupt:
                    print("\nUse 'exit' or 'quit' to leave the interactive session.")
                    continue
                except EOFError:
                    print("\nGoodbye!")
                    break
        finally:
            # Clean up by removing this CLI as the handler from the kernel
            self.gcs_runtime.kernel.set_input_handler(None)
            self.gcs_runtime.kernel.set_output_handler(None)
            
            # Stop the kernel system to properly terminate all background threads
            try:
                self.gcs_runtime.kernel.stop_system()
            except Exception as e:
                print(f"\nWarning: Error during kernel shutdown: {e}")
            
            # Mark that shutdown has been initiated to prevent double shutdown in main
            self.gcs_runtime.shutdown_initiated = True
    
    def _handle_input(self, user_input: str) -> str:
        """
        Handle input through the kernel by processing it in this CLI.
        
        Args:
            user_input: Raw user input string
            
        Returns:
            String response to user
        """
        # Process the input the same way as before
        return self.process_input(user_input)
    
    def _handle_output(self, output_data: str):
        """
        Handle output through the kernel by displaying it in this CLI.
        
        Args:
            output_data: The output data to display
        """
        print(output_data)
    
    def process_input(self, user_input: str) -> str:
        """
        Process user input, either as natural language or direct command.
        
        Args:
            user_input: Raw user input string
            
        Returns:
            String response to user
        """
        # Clean up the input
        user_input = user_input.strip()
        
        if not user_input:
            return ""
        
        # Check for built-in commands first
        if user_input.lower() in ['help', 'h']:
            return (
                "Cogniscient Interactive CLI Help:\n"
                "- Natural language commands: Just type what you want to do\n"
                "- Direct commands: Use standard CLI commands (list-configs, run, etc.)\n"
                "- 'status': Show current system status\n"
                "- 'help': Show this help\n"
                "- 'exit' or 'quit': Exit the interactive session\n"
                "- 'history': Show recent conversation history\n"
                "- 'clear': Clear the session context\n"
            )
        
        elif user_input.lower() in ['status', 'info']:
            info = self.session_manager.get_session_info()
            active_agents = info['active_agents']
            current_config = info.get('active_config', 'None')
            interaction_count = info['interaction_count']
            
            # Check authentication status
            try:
                auth_status = asyncio.run(self._get_auth_status())
            except RuntimeError:
                # Handle case where we're already in a running event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in a running loop, we need to use a different approach
                    # For now, we'll just return a temporary status
                    auth_status = "Unable to check authentication status - event loop issue"
                except RuntimeError:
                    # No event loop running
                    auth_status = "Unable to check authentication status"
            except:
                auth_status = "Unable to check authentication status"
            
            return (
                f"System Status:\n"
                f"- Active agents: {', '.join(active_agents) if active_agents else 'None'}\n"
                f"- Current config: {current_config}\n"
                f"- Interactions in session: {interaction_count}\n"
                f"- Authentication: {auth_status}\n"
                f"- Current provider: {self.gcs_runtime.llm_service.provider_manager.current_provider if hasattr(self.gcs_runtime.llm_service, 'provider_manager') else 'Unknown'}"
            )
            
        elif user_input.lower() in ['exit', 'quit', 'bye']:
            try:
                self.session_manager.close_session()
            except Exception as e:
                print(f"Warning: Error during session cleanup: {e}")
            return "Goodbye! Exiting interactive session."
        
        elif user_input.lower() == 'history':
            # Show recent conversation history
            recent_context = self.session_manager.get_recent_context(3)
            if not recent_context:
                return "No recent interactions to show."
            
            history_str = "Recent interactions:\n"
            for i, interaction in enumerate(recent_context, 1):
                timestamp = interaction['timestamp'].strftime("%H:%M:%S")
                history_str += f"{i}. [{timestamp}] You: {interaction['user_input']}\n"
                history_str += f"   System: {interaction['response']}\n"
            return history_str
        
        elif user_input.lower().startswith('ref '):
            # Reference a previous interaction by index
            try:
                ref_parts = user_input.split(' ', 1)
                if len(ref_parts) < 2:
                    return "Usage: ref <index> [additional_command]"
                
                ref_index = int(ref_parts[1].split()[0]) - 1  # Convert to 0-based index
                interaction = self.session_manager.get_interaction_by_index(ref_index)
                
                if interaction:
                    response = f"Referenced interaction #{ref_index + 1}:\n"
                    response += f"You: {interaction['user_input']}\n"
                    response += f"System: {interaction['response']}\n"
                    return response
                else:
                    return f"No interaction found at index {ref_index + 1}."
            except (ValueError, IndexError):
                return "Invalid reference. Use 'history' to see available interactions and their indices."
        
        elif user_input.lower() == 'clear':
            # Clear conversation history
            self.session_manager.clear_conversation_history()
            self.session_manager.update_session_context('last_action', 'Cleared conversation history')
            return "Conversation history cleared."
        
        # Authentication-related commands
        elif user_input.lower().startswith('auth login') or user_input.lower() == 'auth':
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in a running loop, we can't use asyncio.run
                    # Instead, we'll need to handle this differently
                    return "Authentication not available in interactive session - event loop issue"
                except RuntimeError:
                    # No event loop running, we can use asyncio.run
                    return asyncio.run(self._perform_auth_login())
            except Exception as e:
                return f"Error in auth command: {str(e)}"
        
        elif user_input.lower() == 'auth-status' or user_input.lower().startswith('auth status'):
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in a running loop, we can't use asyncio.run
                    # Instead, we'll need to handle this differently
                    return "Authentication status not available - event loop issue"
                except RuntimeError:
                    # No event loop running, we can use asyncio.run
                    auth_status = asyncio.run(self._get_auth_status())
                    return f"Authentication status: {auth_status}"
            except Exception as e:
                return f"Error in auth-status command: {str(e)}"
        
        elif user_input.lower().startswith('switch-provider ') or user_input.lower() == 'switch-provider':
            # Handle both 'switch-provider' and 'switch-provider <name>'
            try:
                if user_input.lower() == 'switch-provider':
                    return "Please specify a provider. Usage: switch-provider <provider_name>"
                
                # Normalize the command to a consistent format and extract provider name
                normalized = user_input.lower().replace('switch provider ', 'switch-provider ')
                # Extract the provider name after 'switch-provider '
                parts = normalized.split(' ', 1)
                if len(parts) == 2:
                    provider_name = parts[1].strip()
                    # Check if we're already in an event loop
                    try:
                        loop = asyncio.get_running_loop()
                        # If we're in a running loop, use run_until_complete
                        return loop.run_until_complete(self._switch_provider(provider_name))
                    except RuntimeError:
                        # No event loop running, we can use asyncio.run
                        return asyncio.run(self._switch_provider(provider_name))
                else:
                    return "Please specify a provider. Usage: switch-provider <provider_name>"
            except Exception as e:
                return f"Error in switch-provider command: {str(e)}"
        
        elif user_input.lower() == 'list-providers' or user_input.lower() == 'list providers':
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in a running loop, we can't use asyncio.run
                    providers = loop.run_until_complete(self.gcs_runtime.llm_service.provider_manager.get_available_providers())
                    return f"Available providers: {', '.join(providers)}"
                except RuntimeError:
                    # No event loop running, we can use asyncio.run
                    providers = asyncio.run(self.gcs_runtime.llm_service.provider_manager.get_available_providers())
                    return f"Available providers: {', '.join(providers)}"
            except Exception as e:
                return f"Error in list-providers command: {str(e)}"
        
        # Check for direct CLI commands - these are handled directly by the GCSRuntime
        elif user_input.lower().startswith('list-configs'):
            configs = self.gcs_runtime.list_available_configurations()
            if configs:
                return f"Available configurations: {', '.join(configs)}"
            else:
                return "No configurations available."
        
        elif user_input.lower().startswith('list-agents'):
            agents = list(self.gcs_runtime.agents.keys())
            if agents:
                return f"Available agents: {', '.join(agents)}"
            else:
                return "No agents available."
        
        # Handle configuration loading commands
        elif user_input.lower().startswith('load config ') or user_input.lower().startswith('load configuration '):
            # Extract configuration name from the command
            parts = user_input.split(' ', 2)  # Split into at most 3 parts: ['load', 'config', 'name']
            if len(parts) >= 3:
                config_name = parts[2].strip()
                try:
                    self.gcs_runtime.load_configuration(config_name)
                    agents = list(self.gcs_runtime.agents.keys())
                    return f"Configuration '{config_name}' loaded successfully. Active agents: {', '.join(agents) if agents else 'None'}"
                except Exception as e:
                    return f"Error loading configuration '{config_name}': {str(e)}"
            else:
                return "Please specify a configuration name. Available configs: " + \
                       ", ".join(self.gcs_runtime.list_available_configurations())
        
        # For all other inputs, use the kernel for processing
        else:
            try:
                # Create a simple callback to collect events for CLI output
                events_collected = []
                
                def mock_send_stream_event(event_type: str, content: str = None, data: Dict[str, Any] = None):
                    event = {
                        "type": event_type,
                    }
                    if content is not None:
                        event["content"] = content
                    if data is not None:
                        event["data"] = data
                    events_collected.append(event)
                    
                    # For streaming to the CLI, we might want to print events as they come in
                    # This would provide real-time updates to the user as in the web interface
                    if event_type == 'tool_call':
                        tool_data = data or {}
                        tool_name = tool_data.get('agent_name', 'Unknown Tool')
                        tool_method = tool_data.get('method_name', 'Unknown Method')
                        tool_params = tool_data.get('parameters', {})
                        print(f"🔧 Calling tool: {tool_name}.{tool_method} with params: {tool_params}")
                    elif event_type == 'tool_response':
                        tool_data = data or {}
                        tool_result = tool_data.get('result', 'No result')
                        print(f"✅ Tool response: {tool_result}")
                    elif event_type == 'assistant_response':
                        print(f"💬 Assistant: {content}")
                
                # Add the callback to the kernel
                self.gcs_runtime.kernel.add_streaming_callback(mock_send_stream_event)
                
                # Check if we're in an existing event loop and handle accordingly
                try:
                    loop = asyncio.get_running_loop()
                    # We're already in a running loop, so we use run_coroutine_threadsafe to
                    # run the coroutine in the existing loop and get a Future
                    future = asyncio.run_coroutine_threadsafe(
                        self.gcs_runtime.kernel.process_user_input_streaming(user_input),
                        loop
                    )
                    # Wait for the result
                    result = future.result()
                except RuntimeError:
                    # No event loop running, run normally
                    result = asyncio.run(self.gcs_runtime.kernel.process_user_input_streaming(user_input))
                
                # Process the collected events to build a response
                # For CLI, we're mainly interested in the final response
                response = result.get('response', str(result)) if isinstance(result, dict) else str(result)
                
                # Add any tool call information to the response if available
                tool_call_info = ""
                for event in events_collected:
                    if event.get('type') == 'tool_call':
                        tool_data = event.get('data', {})
                        tool_name = tool_data.get('agent_name', 'Unknown Tool')  # Use agent_name instead of name
                        tool_method = tool_data.get('method_name', 'Unknown Method')  # Use method_name
                        tool_args = tool_data.get('parameters', {})
                        tool_call_info += f"\n🔧 Tool Call: {tool_name}.{tool_method}"
                        if tool_args:
                            tool_call_info += f" Parameters: {tool_args}"
                    elif event.get('type') == 'tool_response':
                        tool_data = event.get('data', {})
                        tool_name = tool_data.get('agent_name', 'Unknown Tool')  # Use agent_name instead of name
                        tool_result = tool_data.get('result', tool_data.get('response', 'No result'))
                        tool_call_info += f"\n✅ Tool Response: {tool_name}"
                        if tool_result != 'No result':
                            tool_call_info += f"\nResult: {tool_result}"
                
                # Combine tool call info with the main response
                if tool_call_info and tool_call_info.strip():
                    response = tool_call_info + "\n" + response
            except Exception as e:
                # If async processing fails, provide an error message
                response = f"Error processing with LLM via kernel: {str(e)}"
            
            # Add intelligent context or suggestions based on the response
            return self._add_intelligent_context(user_input, response)
    
    def _add_intelligent_context(self, user_input: str, response: str) -> str:
        """
        Add intelligent context or suggestions based on the user's input and system response.
        
        Args:
            user_input: Original user input
            response: Response from the system
            
        Returns:
            Enhanced response with context or suggestions
        """
        # Identify context keywords to suggest related actions
        lower_input = user_input.lower()
        
        # Add context-aware suggestions
        suggestions = []
        
        if any(keyword in lower_input for keyword in ["config", "configuration"]):
            # If user was asking about configurations, suggest loading one
            configs = self.gcs_runtime.list_available_configurations()
            if configs:
                suggestions.append(f"Tip: You can load a configuration with 'load config {configs[0]}'")
        elif any(keyword in lower_input for keyword in ["agent", "run"]):
            # If user was asking about agents, suggest running one
            agents = list(self.gcs_runtime.agents.keys())
            if agents:
                suggestions.append(f"Tip: Try running an agent with 'run agent {agents[0]}'")
        
        # Add a summary marker if the response is long
        if len(response) > 150:  # If response is long
            lines = response.split("\n")
            if len(lines) > 3:
                # Only return first few lines and suggest to see full details
                preview = "\n".join(lines[:3])
                preview += "\n... (continue with more specific questions for full details)"
                response = preview
        
        # Add suggestions if any
        if suggestions:
            response += f"\n\n{suggestions[0]}"
        
        return response
    async def _get_auth_status(self) -> str:
        """
        Get the authentication status.
        
        Returns:
            String indicating the authentication status
        """
        token_manager = TokenManager(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        
        has_creds = await token_manager.has_valid_credentials()
        if has_creds:
            return "Valid credentials found"
        else:
            return "No valid credentials found"

    async def _perform_auth_login(self) -> str:
        """
        Perform authentication using device flow.
        
        Returns:
            String response to user
        """
        if not settings.qwen_client_id:
            return "Error: Qwen client ID not configured. Please set QWEN_CLIENT_ID in your environment."
        
        oauth_manager = OAuthManager(
            client_id=settings.qwen_client_id,
            authorization_server=settings.qwen_authorization_server,
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        
        print("Starting OAuth device flow...")
        print("Please visit the URL shown below and enter the code when prompted:")
        
        success = await oauth_manager.authenticate_with_device_flow()
        if success:
            return "Authentication successful!"
        else:
            return "Authentication failed!"

    async def _switch_provider(self, provider_name: str) -> str:
        """
        Switch the active provider.
        
        Args:
            provider_name: Name of the provider to switch to
            
        Returns:
            String response to user
        """
        try:
            success = self.gcs_runtime.llm_service.provider_manager.set_provider(provider_name)
            if success:
                return f"Provider switched to: {provider_name}"
            else:
                available = await self.gcs_runtime.llm_service.provider_manager.get_available_providers()
                return f"Failed to switch to provider: {provider_name}. Available providers: {', '.join(available)}"
        except Exception as e:
            return f"Error switching provider: {str(e)}"

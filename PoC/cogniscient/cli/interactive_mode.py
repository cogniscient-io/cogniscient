"""
Interactive mode implementation for Cogniscient CLI.

This module provides the REPL-style interactive interface.
"""
import os
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.orchestrator.chat_interface import ChatInterface
from cogniscient.engine.orchestrator.llm_orchestrator import LLMOrchestrator
from .session_manager import SessionManager

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
        
        # Create a prompt session with history
        history_file = os.path.expanduser("~/.cogniscient_history")
        self.session = PromptSession(history=FileHistory(history_file))
        
        # Define command completions
        self.completer = WordCompleter([
            'help', 'exit', 'quit', 'status', 
            'list-configs', 'list-agents', 'run-agent'
        ])
    
    def start_session(self):
        """
        Start the interactive session.
        """
        print("Cogniscient Interactive CLI v0.1.0")
        
        # Show current system status
        agents = list(self.gcs_runtime.agents.keys())
        print("System status: Ready")
        print(f"Active agents: {', '.join(agents) if agents else 'None'}")
        print("Type 'help' for available commands or just start typing.\\n")
        
        # Add special session start message to history
        self.session_manager.add_interaction("SYSTEM", "Interactive session started")
        
        while True:
            try:
                # Get user input with custom prompt
                user_input = self.session.prompt('Cogniscient> ', completer=self.completer)
                
                # Process the input
                response = self.process_input(user_input)
                
                # Output the response
                print(response)
                
                # Add interaction to history
                self.session_manager.add_interaction(user_input, response)
                
                # Check if user wants to exit
                if user_input.lower().strip() in ['exit', 'quit', 'bye']:
                    break
                    
            except KeyboardInterrupt:
                print("\\nUse 'exit' or 'quit' to leave the interactive session.")
                continue
            except EOFError:
                print("\\nGoodbye!")
                break
    
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
            
            return (
                f"System Status:\n"
                f"- Active agents: {', '.join(active_agents) if active_agents else 'None'}\n"
                f"- Current config: {current_config}\n"
                f"- Interactions in session: {interaction_count}"
            )
            
        elif user_input.lower() in ['exit', 'quit', 'bye']:
            self.session_manager.close_session()
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
        
        # For all other inputs, use the ChatInterface which connects to the LLM
        else:
            try:
                # Run the async process_user_input in a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.chat_interface.process_user_input(user_input)
                    )
                    
                    # Handle the result properly
                    if isinstance(result, dict):
                        # Extract the response if it's in a structured result
                        response = result.get('response', str(result))
                    else:
                        response = str(result)
                finally:
                    loop.close()
            except Exception as e:
                # If async processing fails, provide an error message
                response = f"Error processing with LLM: {str(e)}"
            
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
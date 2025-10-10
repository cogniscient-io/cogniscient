"""
Natural Language Processing module for Cogniscient CLI.

This module interprets natural language input and maps it to system operations.
"""
from typing import Dict, Any, Tuple
from cogniscient.engine.gcs_runtime import GCSRuntime
from .utils import identify_intent, extract_entities

class NLPProcessor:
    """
    Processes natural language input and maps it to system operations.
    """
    
    def __init__(self, gcs_runtime: GCSRuntime):
        """
        Initialize the NLP processor with a GCS runtime instance.
        
        Args:
            gcs_runtime: GCS runtime instance for context and operations
        """
        self.gcs_runtime = gcs_runtime
    
    def process_input(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process user input and determine the appropriate action.
        
        Args:
            user_input: Raw user input string
            
        Returns:
            Tuple of (intent, extracted_parameters)
        """
        intent = identify_intent(user_input)
        entities = extract_entities(user_input, self.gcs_runtime)
        
        # Also store the raw input for potential LLM processing
        entities['_raw_input'] = user_input
        
        return intent, entities
    
    def execute_intent(self, intent: str, params: Dict[str, Any]) -> str:
        """
        Execute the identified intent with the given parameters.
        
        Args:
            intent: The identified intent
            params: Extracted parameters
            
        Returns:
            String response to user
        """
        if intent == "list_configs":
            configs = self.gcs_runtime.list_available_configurations()
            if configs:
                return f"Available configurations: {', '.join(configs)}"
            else:
                return "No configurations available."
        
        elif intent == "list_agents":
            agents = list(self.gcs_runtime.agents.keys())
            if agents:
                return f"Available agents: {', '.join(agents)}"
            else:
                return "No agents available."
        
        elif intent == "run_agent":
            agent_name = params.get("agent")
            method_name = params.get("method", "run")  # Default to "run" method
            
            if not agent_name:
                return "I couldn't identify which agent to run. Please specify an agent name."
            
            try:
                result = self.gcs_runtime.run_agent(agent_name, method_name)
                return f"Ran {agent_name}.{method_name}(): {result}"
            except Exception as e:
                return f"Error running {agent_name}.{method_name}(): {str(e)}"
        
        elif intent == "help":
            return (
                "Available commands:\n"
                "- 'What configurations are available?' - List available configurations\n"
                "- 'What agents are available?' - List available agents\n"
                "- 'Run agent <name> with method <method>' - Run a specific agent method\n"
                "- 'Load configuration <name>' - Load a specific configuration\n"
                "- 'help' - Show this help message\n"
                "- You can also use traditional CLI commands like 'list-configs', 'run', etc."
            )
        
        elif intent == "status":
            agents = list(self.gcs_runtime.agents.keys())
            return f"System status: Ready. Active agents: {len(agents)}. Available agents: {', '.join(agents)}"
        
        elif intent == "load_config":
            config_name = params.get("configuration")
            if not config_name:
                # If no config name was extracted, return a helpful error
                return "Which configuration would you like to load? Available configs: " + \
                       ", ".join(self.gcs_runtime.list_available_configurations())
            
            try:
                self.gcs_runtime.load_configuration(config_name)
                return f"Configuration '{config_name}' loaded successfully."
            except Exception as e:
                return f"Error loading configuration '{config_name}': {str(e)}"
        
        elif intent == "natural_language":
            # For inputs that don't match specific intents, try to be helpful
            return self._handle_general_natural_language(params)
        else:
            return "I'm not sure how to handle that command. Try 'help' for available options."
    
    def _handle_general_natural_language(self, params: Dict[str, Any]) -> str:
        """
        Handle inputs that don't match specific intents.
        
        Args:
            params: Extracted parameters from the input
            
        Returns:
            String response to user
        """
        if params:
            # If there are entities extracted but no specific intent, try to infer
            if params.get("configuration"):
                try:
                    config_name = params["configuration"]
                    self.gcs_runtime.load_configuration(config_name)
                    return f"Configuration '{config_name}' loaded successfully."
                except Exception:
                    config_name = params["configuration"]
                    return f"I couldn't load the configuration '{config_name}'."
            
            elif params.get("agent"):
                try:
                    agent_name = params["agent"]
                    result = self.gcs_runtime.run_agent(agent_name, "run")
                    return f"Ran {agent_name}.run(): {result}"
                except Exception:
                    agent_name = params["agent"]
                    return f"I couldn't run the agent '{agent_name}'."
        
        # For more intelligent responses when we can't understand the input,
        # we should try to use the LLM service if it's available
        try:
            # Use the llm_service to generate a response to the user's query
            if hasattr(self.gcs_runtime, 'llm_service'):
                # Create a contextual prompt for the LLM
                llm_content = (
                    f"User asked: '{params.get('_raw_input', 'a general question') if params else 'a general question'}'. "
                    "The Cogniscient system doesn't have specific configurations or agents loaded to handle this request. "
                    "Please provide a helpful response to the user's query in the context of the Cogniscient system, "
                    "suggesting they might need to load configurations or agents to get specific functionality. "
                    "Be friendly and informative."
                )
                
                # For now, return a placeholder since we can't run the async llm_service.generate_response
                # In a real implementation, this would await the response
                return (
                    "I'm not sure how to handle that. Try 'help' for available commands, "
                    "or use specific commands like 'list-configs', 'run', etc."
                )
        except Exception:
            pass  # If LLM service fails, fall back to default
        
        # Default response when we can't understand the input
        return (
            "I'm not sure how to handle that. Try 'help' for available commands, "
            "or use specific commands like 'list-configs', 'run', etc."
        )
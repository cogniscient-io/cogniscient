"""Chat Interface for LLM-Enhanced Adaptive Control System."""

import logging
import re
from typing import Dict, Any, List
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ChatInterface:
    """Chat interface for human-in-the-loop interaction with the LLM orchestrator."""

    def __init__(self, orchestrator):
        """Initialize chat interface with orchestrator.
        
        Args:
            orchestrator: The LLM orchestrator instance.
        """
        self.orchestrator = orchestrator
        self.llm_service = LLMService()
        self.conversation_history: List[Dict[str, str]] = []

    async def process_user_input(self, user_input: str) -> dict:
        """Process user input and generate response using LLM-driven agent selection.
        
        Args:
            user_input (str): The user's input message.
            
        Returns:
            dict: A dictionary containing the response and tool call information.
        """
        # Check for special commands
        if user_input.lower().startswith("load config "):
            config_name = user_input[12:].strip()
            return await self._handle_load_config(config_name)
        elif user_input.lower() == "list configs":
            return await self._handle_list_configs()
        elif user_input.lower() == "list agents":
            return await self._handle_list_agents()
            
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Generate response using LLM orchestrator which handles agent selection
        result = await self.orchestrator.process_user_request(user_input, self.conversation_history)
        
        # Add response to conversation history
        self.conversation_history.append({"role": "assistant", "content": result.get("response", result)})
        
        return result
    
    async def _handle_load_config(self, config_name: str) -> dict:
        """Handle loading a configuration.
        
        Args:
            config_name (str): Name of the configuration to load.
            
        Returns:
            dict: Response indicating success or failure.
        """
        try:
            self.orchestrator.ucs_runtime.load_configuration(config_name)
            agents_list = ", ".join(self.orchestrator.ucs_runtime.agents.keys())
            response = f"Successfully loaded configuration '{config_name}'. Available agents: {agents_list}"
            return {"response": response}
        except Exception as e:
            return {"response": f"Failed to load configuration '{config_name}': {str(e)}"}

    async def _handle_list_configs(self) -> dict:
        """Handle listing available configurations.
        
        Returns:
            dict: Response with list of available configurations.
        """
        try:
            configs = self.orchestrator.ucs_runtime.list_available_configurations()
            if configs:
                response = f"Available configurations: {', '.join(configs)}"
            else:
                response = "No configurations available."
            return {"response": response}
        except Exception as e:
            return {"response": f"Failed to list configurations: {str(e)}"}

    async def _handle_list_agents(self) -> dict:
        """Handle listing loaded agents.
        
        Returns:
            dict: Response with list of loaded agents.
        """
        agents = list(self.orchestrator.ucs_runtime.agents.keys())
        if agents:
            response = f"Currently loaded agents: {', '.join(agents)}"
        else:
            response = "No agents currently loaded."
        return {"response": response}
    
    async def handle_approval_request(self, request: Dict[str, Any]) -> bool:
        """Handle approval requests from the orchestrator.
        
        Args:
            request (Dict[str, Any]): The approval request details.
            
        Returns:
            bool: True if approved, False otherwise.
        """
        # In a real implementation, this would present the approval request to the user
        # and wait for their response. For now, we'll log the request and return False.
        logger.warning(f"Approval request received: {request}")
        # For this implementation, we'll return False to indicate denial
        # A real implementation would have a mechanism to get user input
        return False
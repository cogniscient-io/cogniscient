"""LLM Orchestration Engine for Adaptive Control System."""

import logging
from typing import AsyncGenerator, Callable, Dict, Any, List
from cogniscient.engine.ucs_runtime import UCSRuntime
from cogniscient.engine.orchestrator.llm_evaluation import LLMEvaluation
from cogniscient.engine.orchestrator.user_request_processor import UserRequestProcessor
from cogniscient.engine.orchestrator.parameter_adaptation import ParameterAdaptation
from cogniscient.engine.config.settings import settings

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """LLM Orchestration Engine for managing agents and their adaptations."""

    def __init__(self, ucs_runtime: UCSRuntime):
        """Initialize the LLM orchestrator with UCS runtime.
        
        Args:
            ucs_runtime (UCSRuntime): The UCS runtime instance to manage agents.
        """
        self.ucs_runtime = ucs_runtime
        # Use the LLM service from UCS runtime directly
        self.llm_service = ucs_runtime.llm_service
        
        # Initialize the separate modules
        self.evaluator = LLMEvaluation(self.llm_service)
        self.user_request_processor = UserRequestProcessor(ucs_runtime, self.llm_service)
        self.parameter_adaptation = ParameterAdaptation(ucs_runtime)

    async def evaluate_agent_output(self, agent_name: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate agent output using LLM and determine next actions.
        
        Args:
            agent_name (str): Name of the agent that produced the output.
            output (Dict[str, Any]): The output from the agent.
            
        Returns:
            Dict[str, Any]: The evaluation result with next actions.
        """
        return await self.evaluator.evaluate_agent_output(agent_name, output)

    async def process_user_request_streaming(self, user_input: str, conversation_history: List[Dict[str, str]], 
                                           send_stream_event: Callable[[str, str, Dict[str, Any]], Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process user request using LLM to determine appropriate agents with streaming support.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            send_stream_event (Callable): Function to send streaming events
            
        Yields:
            dict: Streaming events containing response parts, tool calls, etc.
        """
        return await self.user_request_processor.process_user_request_streaming(
            user_input, conversation_history, send_stream_event
        )

    def is_within_range(self, agent_name: str, param: str, value: Any) -> bool:
        """Check if a parameter value is within the acceptable range.
        
        Args:
            agent_name (str): Name of the agent.
            param (str): Parameter name.
            value (Any): Parameter value to check.
            
        Returns:
            bool: True if value is within range, False otherwise.
        """
        return self.parameter_adaptation.is_within_range(agent_name, param, value)

    async def adapt_parameters(self, agent_name: str, suggested_changes: Dict[str, Any]) -> bool:
        """Adapt agent parameters within predefined ranges.
        
        Args:
            agent_name (str): Name of the agent to adapt.
            suggested_changes (Dict[str, Any]): Suggested parameter changes.
            
        Returns:
            bool: True if changes were applied, False if escalation is needed.
        """
        return await self.parameter_adaptation.adapt_parameters(agent_name, suggested_changes)

    async def request_approval(self, agent_name: str, changes: Dict[str, Any]) -> bool:
        """Request human approval for significant parameter changes.
        
        Args:
            agent_name (str): Name of the agent.
            changes (Dict[str, Any]): Parameter changes requiring approval.
            
        Returns:
            bool: True if approved, False otherwise.
        """
        return await self.parameter_adaptation.request_approval(agent_name, changes)

    async def orchestrate_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Orchestrate an agent execution with LLM evaluation.
        
        Args:
            agent_name (str): Name of the agent to execute.
            method_name (str): Name of the method to execute.
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.
            
        Returns:
            Dict[str, Any]: The result of the orchestration.
        """
        try:
            # Run the agent method
            result = self.ucs_runtime.run_agent(agent_name, method_name, *args, **kwargs)
            
            # Evaluate the result with LLM
            evaluation = await self.evaluate_agent_output(agent_name, result)
            
            # Process the evaluation decision
            decision = evaluation.get("decision", "failure")
            if decision == "adjust":
                # Extract suggested changes from evaluation
                changes = evaluation.get("suggested_changes", {})
                await self.adapt_parameters(agent_name, changes)
            elif decision == "escalate":
                await self.request_approval(agent_name, {})
                
            return {
                "agent": agent_name,
                "method": method_name,
                "result": result,
                "evaluation": evaluation
            }
        except Exception as e:
            logger.error(f"Error orchestrating agent {agent_name}: {e}")
            return {
                "agent": agent_name,
                "method": method_name,
                "error": str(e)
            }

    async def process_user_request(self, user_input: str, conversation_history: List[Dict[str, str]]) -> dict:
        """Process user request using LLM to determine appropriate agents.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            dict: A dictionary containing the final response and tool call information.
        """
        return await self.user_request_processor.process_user_request(user_input, conversation_history)
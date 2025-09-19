"""LLM Orchestration Engine for Adaptive Control System."""

import json
import logging
from typing import Dict, Any
from src.services.llm_service import LLMService
from src.services.contextual_llm_service import ContextualLLMService
from src.ucs_runtime import UCSRuntime

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """LLM Orchestration Engine for managing agents and their adaptations."""

    def __init__(self, ucs_runtime: UCSRuntime):
        """Initialize the LLM orchestrator with UCS runtime.
        
        Args:
            ucs_runtime (UCSRuntime): The UCS runtime instance to manage agents.
        """
        self.ucs_runtime = ucs_runtime
        self.raw_llm_service = LLMService()  # Generic transport layer
        self.llm_service = ContextualLLMService(self.raw_llm_service)  # High-level service with context
        self.parameter_ranges: Dict[str, Dict[str, Dict[str, Any]]] = {}  # Define acceptable parameter ranges
        self.approval_thresholds: Dict[str, Dict[str, Any]] = {}  # Define thresholds for human approval

    async def evaluate_agent_output(self, agent_name: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate agent output using LLM and determine next actions.
        
        Args:
            agent_name (str): Name of the agent that produced the output.
            output (Dict[str, Any]): The output from the agent.
            
        Returns:
            Dict[str, Any]: The evaluation result with next actions.
        """
        # Construct prompt for LLM evaluation
        prompt = f"Agent {agent_name} produced output: {json.dumps(output)}\
"
        prompt += "Based on this output, what should be the next steps?\
"
        prompt += "Please respond with a JSON object that has the following structure:\
"
        prompt += "{\
"
        prompt += '  "decision": "success|retry|failure",\
'
        prompt += '  "reasoning": "Explanation for the decision",\
'
        prompt += '  "retry_params": {"param_name": "param_value"} // Only include this if decision is "retry"\
'
        prompt += "}\
"
        prompt += "Use 'success' if the task completed successfully.\
"
        prompt += "Use 'retry' if the task should be retried, possibly with different parameters. When suggesting retry_params, consider adjusting timeout values or other relevant settings.\
"
        prompt += "Use 'failure' if the task cannot be completed successfully.\
"
        prompt += "IMPORTANT: Respond ONLY with the JSON object. Do not include any other text, markdown, or formatting.\
"
        
        try:
            # Get LLM evaluation using the contextual LLM service
            evaluation_text = await self.llm_service.generate_response(prompt)
            
            # Clean up the response text
            # Remove any markdown code block markers
            evaluation_text = evaluation_text.strip()
            if evaluation_text.startswith("```json"):
                evaluation_text = evaluation_text[7:]
            if evaluation_text.startswith("```"):
                evaluation_text = evaluation_text[3:]
            if evaluation_text.endswith("```"):
                evaluation_text = evaluation_text[:-3]
            evaluation_text = evaluation_text.strip()
            
            # Try to parse as JSON
            try:
                evaluation = json.loads(evaluation_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                # This handles cases where the LLM includes additional text around the JSON
                import re
                # Look for a JSON object in the response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', evaluation_text)
                if json_match:
                    try:
                        evaluation = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        evaluation = {"decision": "failure", "reasoning": f"Could not parse LLM response as JSON: {evaluation_text}"}
                else:
                    evaluation = {"decision": "failure", "reasoning": f"Could not find JSON in LLM response: {evaluation_text}"}
            
            # Validate the structure of the evaluation
            if "decision" not in evaluation:
                evaluation["decision"] = "failure"
                evaluation["reasoning"] = f"Missing 'decision' field in LLM response: {evaluation}"
            
            return evaluation
        except Exception as e:
            logger.error(f"Error evaluating agent output: {e}")
            return {"decision": "failure", "reasoning": f"Error in evaluation: {str(e)}"}

    def is_within_range(self, agent_name: str, param: str, value: Any) -> bool:
        """Check if a parameter value is within the acceptable range.
        
        Args:
            agent_name (str): Name of the agent.
            param (str): Parameter name.
            value (Any): Parameter value to check.
            
        Returns:
            bool: True if value is within range, False otherwise.
        """
        if agent_name not in self.parameter_ranges:
            return True  # No ranges defined, allow all values
            
        agent_ranges = self.parameter_ranges[agent_name]
        if param not in agent_ranges:
            return True  # No range defined for this parameter, allow all values
            
        param_range = agent_ranges[param]
        min_val = param_range.get("min")
        max_val = param_range.get("max")
        
        # Check if value is within range
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True

    async def adapt_parameters(self, agent_name: str, suggested_changes: Dict[str, Any]) -> bool:
        """Adapt agent parameters within predefined ranges.
        
        Args:
            agent_name (str): Name of the agent to adapt.
            suggested_changes (Dict[str, Any]): Suggested parameter changes.
            
        Returns:
            bool: True if changes were applied, False if escalation is needed.
        """
        current_config = self.ucs_runtime.agent_configs.get(agent_name, {})
        new_config = current_config.copy()
        
        # Check if any changes are outside acceptable ranges
        for param, value in suggested_changes.items():
            if not self.is_within_range(agent_name, param, value):
                # Escalate for approval if outside range
                return await self.request_approval(agent_name, {param: value})
        
        # Apply changes within acceptable ranges
        for param, value in suggested_changes.items():
            # Navigate nested dictionaries to set the parameter
            param_parts = param.split(".")
            target = new_config
            for part in param_parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[param_parts[-1]] = value
        
        # Update agent configuration
        self.ucs_runtime.agent_configs[agent_name] = new_config
        logger.info(f"Adapted parameters for {agent_name}: {suggested_changes}")
        return True

    async def request_approval(self, agent_name: str, changes: Dict[str, Any]) -> bool:
        """Request human approval for significant parameter changes.
        
        Args:
            agent_name (str): Name of the agent.
            changes (Dict[str, Any]): Parameter changes requiring approval.
            
        Returns:
            bool: True if approved, False otherwise.
        """
        # In a real implementation, this would integrate with a chat interface
        # or external approval system. For now, we'll log the request.
        logger.warning(f"Approval requested for {agent_name} changes: {changes}")
        # For this implementation, we'll return False to indicate escalation
        return False

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
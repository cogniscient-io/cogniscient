"""Module for parameter adaptation functionality in LLM Orchestration Engine."""

import logging
from typing import Dict, Any
from cogniscient.engine.ucs_runtime import UCSRuntime

logger = logging.getLogger(__name__)


class ParameterAdaptation:
    """Handles adaptation of agent parameters within predefined ranges."""

    def __init__(self, ucs_runtime: UCSRuntime):
        """Initialize the parameter adaptation module.
        
        Args:
            ucs_runtime (UCSRuntime): The UCS runtime instance to manage agents.
        """
        self.ucs_runtime = ucs_runtime
        self.parameter_ranges: Dict[str, Dict[str, Dict[str, Any]]] = {}  # Define acceptable parameter ranges
        self.approval_thresholds: Dict[str, Dict[str, Any]] = {}  # Define thresholds for human approval

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
"""Module for parameter adaptation functionality in LLM Orchestration Engine."""

import logging
from typing import Dict, Any, Optional
from cogniscient.engine.gcs_runtime import GCSRuntime

logger = logging.getLogger(__name__)


class ParameterAdaptation:
    """Handles adaptation of agent parameters within predefined ranges."""

    def __init__(self, gcs_runtime: GCSRuntime, parameter_ranges: Optional[Dict] = None, approval_thresholds: Optional[Dict] = None):
        """Initialize the parameter adaptation module.
        
        Args:
            gcs_runtime (GCSRuntime): The GCS runtime instance to manage agents.
            parameter_ranges (Dict, optional): Preloaded parameter ranges.
            approval_thresholds (Dict, optional): Preloaded approval thresholds.
        """
        self.gcs_runtime = gcs_runtime
        self.parameter_ranges = parameter_ranges or {}  # Define acceptable parameter ranges
        self.approval_thresholds = approval_thresholds or {}  # Define thresholds for human approval

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
            
        # Handle nested parameter paths (e.g. "dns_settings.timeout")
        param_parts = param.split('.')
        range_config = agent_ranges
        
        for part in param_parts:
            if part in range_config:
                range_config = range_config[part]
            else:
                # If the specific nested parameter isn't defined, 
                # check for a general configuration
                range_config = agent_ranges.get("default_values", {})
                break

        min_val = None
        max_val = None
        
        # Check if range_config is a dictionary with min/max values
        if isinstance(range_config, dict):
            min_val = range_config.get("min") or range_config.get("min_values", {}).get(param.split('.')[-1])
            max_val = range_config.get("max") or range_config.get("max_values", {}).get(param.split('.')[-1])
        # If range_config is a direct value with min/max
        elif hasattr(range_config, '__getitem__'):
            try:
                min_val = range_config.get("min_values", {}).get(param.split('.')[-1])
                max_val = range_config.get("max_values", {}).get(param.split('.')[-1])
            except AttributeError:
                # If it's not subscriptable, fallback to True
                return True
        
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
        current_config = self.gcs_runtime.agent_configs.get(agent_name, {})
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
        self.gcs_runtime.agent_configs[agent_name] = new_config
        logger.info(f"Adapted parameters for {agent_name}: {suggested_changes}")
        
        # If there's an MCP server available, update tools for the agent after config changes
        if hasattr(self.gcs_runtime, 'llm_orchestrator') and hasattr(self.gcs_runtime.llm_orchestrator, 'mcp_server'):
            await self._update_mcp_tools_for_agent(agent_name)
        
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
        
        # Check if the orchestrator has a chat interface to handle the approval
        if hasattr(self.gcs_runtime, 'llm_orchestrator'):
            orchestrator = self.gcs_runtime.llm_orchestrator
            if hasattr(orchestrator, 'chat_interface'):
                approval_result = await orchestrator.chat_interface.handle_approval_request({
                    "agent_name": agent_name,
                    "changes": changes
                })
                return approval_result
        
        # For this implementation, we'll return False to indicate escalation
        return False
    
    async def _update_mcp_tools_for_agent(self, agent_name: str):
        """Update MCP tools for a specific agent after configuration changes."""
        # This method would inform the MCP server that agent configuration has changed
        # and tools might need to be updated or re-registered
        if hasattr(self.gcs_runtime, 'llm_orchestrator') and hasattr(self.gcs_runtime.llm_orchestrator, 'mcp_server'):
            # In a real implementation, this would notify the MCP server to update tools
            # for this specific agent, potentially changing tool schemas based on new configs
            pass
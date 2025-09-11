"""Simple orchestration for the Universal Control System (UCS) PoC."""

import json
from typing import Any, Dict, List
from ucs_runtime import UCSRuntime


class SimpleOrchestrator:
    """Basic orchestrator for executing agent sequences."""

    def __init__(self, ucs_runtime: UCSRuntime):
        """Initialize the orchestrator.
        
        Args:
            ucs_runtime (UCSRuntime): The UCS runtime to use for agent execution.
        """
        self.ucs_runtime = ucs_runtime

    def load_plan(self, plan_file: str) -> Dict[str, Any]:
        """Load an execution plan from a JSON file.
        
        Args:
            plan_file (str): Path to the plan file.
            
        Returns:
            dict: The loaded plan.
        """
        with open(plan_file, "r") as f:
            return json.load(f)

    def execute_plan(self, plan: Dict[str, Any]) -> List[Any]:
        """Execute a plan by running a sequence of agent methods.
        
        Args:
            plan (dict): The execution plan.
            
        Returns:
            list: Results from each step in the plan.
        """
        results = []
        
        for step in plan.get("steps", []):
            agent_name = step["agent"]
            method_name = step["method"]
            args = step.get("args", [])
            kwargs = step.get("kwargs", {})
            
            try:
                result = self.ucs_runtime.run_agent(agent_name, method_name, *args, **kwargs)
                results.append({"step": step, "result": result, "success": True})
                print(f"Step completed: {agent_name}.{method_name}")
            except Exception as e:
                error_result = {"step": step, "error": str(e), "success": False}
                results.append(error_result)
                print(f"Step failed: {agent_name}.{method_name} - {e}")
                # In a more complex system, we might have error handling strategies here
        
        return results


if __name__ == "__main__":
    # This is just for testing the orchestrator independently
    # The main execution flow is in ucs_runtime.py
    pass
"""Main application entry point."""

from control_system.manager import ControlSystemManager
from agents.sample_agent_a import SampleAgentA
from agents.sample_agent_b import SampleAgentB


def main():
    """Main application entry point."""
    manager = ControlSystemManager()
    
    # Load agents
    agent_a = SampleAgentA()
    agent_b = SampleAgentB()
    
    # Add agents to manager
    manager.add_agent(agent_a)
    manager.add_agent(agent_b)
    
    # Generate configurations
    manager.generate_all_configs()
    
    # Demonstrate functionality
    print("Loaded agents:")
    for agent_name in manager.list_agents():
        print(f"  - {agent_name}")


if __name__ == "__main__":
    main()
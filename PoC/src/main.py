"""Main entry point for the dynamic control system."""

from control_system.manager import ControlSystemManager
from agents.sample_agent_a import SampleAgentA
from agents.sample_agent_b import SampleAgentB


def main():
    """Main function to run the control system."""
    # Initialize the control system manager
    manager = ControlSystemManager()
    
    # Create and add sample agents
    agent_a = SampleAgentA()
    agent_b = SampleAgentB()
    
    manager.add_agent(agent_a)
    manager.add_agent(agent_b)
    
    # Generate configuration files for all agents
    manager.generate_all_configs()
    
    print("Configuration files generated successfully.")


if __name__ == "__main__":
    main()
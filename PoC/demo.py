"""Demo script for the Universal Control System (UCS) PoC."""

from ucs_runtime import UCSRuntime
from simple_orchestrator import SimpleOrchestrator


def main():
    """Main demo function."""
    print("Starting UCS PoC Demo")
    
    # Initialize the UCS runtime
    ucs = UCSRuntime()
    ucs.load_all_agents()
    
    # Initialize the orchestrator
    orchestrator = SimpleOrchestrator(ucs)
    
    # Load and execute the demo plan
    print("\nLoading demo plan...")
    plan = orchestrator.load_plan("demo_plan.json")
    
    print("\nExecuting demo plan...")
    results = orchestrator.execute_plan(plan)
    
    # Display results
    print("\nDemo Results:")
    for i, result in enumerate(results):
        print(f"\nStep {i+1}:")
        print(f"  Agent: {result['step']['agent']}")
        print(f"  Method: {result['step']['method']}")
        if result['success']:
            print(f"  Result: {result['result']}")
        else:
            print(f"  Error: {result['error']}")
    
    # Shutdown
    ucs.shutdown()
    print("\nDemo completed.")


if __name__ == "__main__":
    main()
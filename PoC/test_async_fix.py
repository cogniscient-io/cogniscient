#!/usr/bin/env python3
"""
Test script to verify the async task management fix in Cogniscient CLI
"""

import asyncio
import sys
from cogniscient.ui.cli.interactive_mode import InteractiveCLI
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings

async def test_async_operations():
    """Test async operations to ensure no task management issues"""
    print("Testing async operations in Cogniscient...")
    
    # Initialize the GCS runtime
    gcs = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
    
    # Create and test the interactive CLI
    interactive_cli = InteractiveCLI(gcs)
    
    # Test processing a simple input to trigger the async code path
    test_input = "hi"
    
    try:
        response = interactive_cli.process_input(test_input)
        print(f"Response to '{test_input}': {response}")
        
        # Test async methods directly
        # Simulate the type of async operations that were causing issues
        await gcs.shutdown()
        print("✓ Shutdown completed successfully")
        
        return True
    except Exception as e:
        print(f"✗ Error during async operations: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Testing async task management fix...")
    
    # Run the async test
    success = asyncio.run(test_async_operations())
    
    if success:
        print("\n✓ All async operations completed successfully - no task management issues detected!")
        return 0
    else:
        print("\n✗ Issues detected with async task management.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
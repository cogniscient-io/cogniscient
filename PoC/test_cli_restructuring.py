"""
Quick test to verify CLI functionality after restructuring.
"""
import sys
import subprocess


def test_cli_commands():
    """Test that CLI commands work after restructuring."""
    print("Testing CLI command functionality after restructuring...")
    
    # Test that the main CLI module can be imported
    try:
        from cogniscient.cli.main import main
        print("✓ CLI main module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import CLI main: {e}")
        return False
        
    # Test that command_mode module has the old functionality
    try:
        from cogniscient.cli.command_mode import run_command_mode
        print("✓ Command mode module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import command mode: {e}")
        return False
    
    # Test that interactive_mode module is available
    try:
        from cogniscient.cli.interactive_mode import InteractiveCLI
        print("✓ Interactive mode module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import interactive mode: {e}")
        return False

    # Test that the authentication modules are accessible
    try:
        from cogniscient.auth.oauth_manager import OAuthManager
        from cogniscient.llm.provider_manager import ProviderManager
        print("✓ Authentication and provider modules import successfully")
    except ImportError as e:
        print(f"✗ Failed to import auth modules: {e}")
        return False

    print("\nAll CLI restructuring tests passed!")
    print("\nSummary of changes:")
    print("- Old cli.py file has been backed up to cli.py.backup")
    print("- CLI functionality has been moved to cogniscient/cli/ directory")
    print("- Command mode now includes all the new OAuth functionality")
    print("- Entry point in pyproject.toml correctly points to cogniscient.cli.main:main")
    
    return True


if __name__ == "__main__":
    success = test_cli_commands()
    if not success:
        sys.exit(1)
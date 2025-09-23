"""Debug script for additional prompt info functionality."""

from src.ucs_runtime import UCSRuntime


def debug_additional_prompt_info():
    """Debug additional prompt info loading."""
    print("=== Debugging Additional Prompt Info ===")
    
    # Initialize UCS runtime
    ucs_runtime = UCSRuntime()
    
    # Load website only configuration
    print("Loading website_only configuration...")
    ucs_runtime.load_configuration("website_only")
    
    # Check that additional prompt info was loaded
    print(f"Additional prompt info: {ucs_runtime.additional_prompt_info}")
    print(f"Type: {type(ucs_runtime.additional_prompt_info)}")
    print(f"Keys: {list(ucs_runtime.additional_prompt_info.keys())}")


if __name__ == "__main__":
    debug_additional_prompt_info()
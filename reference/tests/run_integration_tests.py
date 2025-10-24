"""
Test runner for integration tests in the GCS Kernel project.
"""

import subprocess
import sys
import os


def run_integration_tests():
    """
    Run all integration tests in the project.
    """
    project_root = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(project_root, "tests", "integration")
    
    # Run pytest on the integration tests
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        test_dir, 
        "-v",  # Verbose output
        "--tb=short"  # Short traceback format
    ], cwd=project_root)
    
    return result.returncode


if __name__ == "__main__":
    print("Running integration tests...")
    exit_code = run_integration_tests()
    sys.exit(exit_code)
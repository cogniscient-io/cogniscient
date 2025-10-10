#!/usr/bin/env python3
"""Test script to verify the exit functionality works properly."""

import subprocess
import time
import signal
import os

def test_exit():
    print("Starting cogniscient process...")
    
    # Start the process
    process = subprocess.Popen(
        ['cogniscient'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a bit for the process to start
    time.sleep(1)
    
    print("Sending 'exit' command...")
    # Send 'exit' to the process
    process.stdin.write('exit\n')
    process.stdin.flush()
    
    print("Waiting for process to terminate...")
    try:
        # Wait for the process to finish with a timeout
        stdout, stderr = process.communicate(timeout=5)
        print(f"Process exited with return code: {process.returncode}")
        print("STDOUT:")
        print(stdout)
        print("STDERR:")
        print(stderr)
    except subprocess.TimeoutExpired:
        print("Process did not terminate within timeout. Killing it...")
        process.kill()
        stdout, stderr = process.communicate()
        print(f"Killed process, return code: {process.returncode}")
        print("STDOUT:")
        print(stdout)
        print("STDERR:")
        print(stderr)

if __name__ == "__main__":
    test_exit()
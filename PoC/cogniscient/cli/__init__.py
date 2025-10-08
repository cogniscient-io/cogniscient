"""
Cogniscient CLI package.

This package contains all CLI-related functionality including both 
command-line and interactive modes.
"""
from .main import main

__all__ = ["main"]  # Define main as part of API but import it only when needed
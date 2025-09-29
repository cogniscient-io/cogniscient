"""
Cogniscient - A generic control system engine for managing AI agents and services.

This package provides a Generic Control System (GCS) runtime for loading 
and managing intelligent agents with LLM integration.
"""

from .engine.gcs_runtime import GCSRuntime

__version__ = "0.1.0"
__author__ = "Cogniscient Team"
__license__ = "MIT"

__all__ = [
    "GCSRuntime"
]
"""
Setup file for Cogniscient package.

This file is included to support editable installs with older pip versions.
For newer versions, the pyproject.toml file is used.
"""
from setuptools import setup

if __name__ == "__main__":
    setup(
        name="cogniscient",
        version="0.1.0",
        description="A generic control system engine for managing AI agents and services"
    )
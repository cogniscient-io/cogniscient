"""
Test suite for the GCS Kernel MCP components.

This module contains tests for the MCP client and server components of the GCS Kernel.
"""
import pytest
import asyncio
from gcs_kernel.models import MCPConfig


def test_mcp_config_creation():
    """Test creating an MCPConfig object."""
    config = MCPConfig(
        server_url="http://localhost:8000",
        client_id="test_client",
        client_secret="test_secret"
    )
    
    assert config.server_url == "http://localhost:8000"
    assert config.client_id == "test_client"
    assert config.client_secret == "test_secret"
    assert config.connection_timeout == 30
    assert config.request_timeout == 60
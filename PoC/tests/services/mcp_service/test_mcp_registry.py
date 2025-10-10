"""Tests for MCP Connection Registry functionality."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from cogniscient.engine.services.mcp_registry import MCPConnectionRegistry, MCPConnectionData


def test_mcp_registry_initialization():
    """Test that MCPConnectionRegistry can be initialized."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        registry = MCPConnectionRegistry(registry_file=str(temp_file))
        assert registry is not None
        assert hasattr(registry, 'connections')
        assert hasattr(registry, 'registry_file')
        assert Path(registry.registry_file).exists()


def test_mcp_registry_save_connection():
    """Test saving a connection to the registry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        
        registry = MCPConnectionRegistry(registry_file=str(temp_file))
        connection_data = MCPConnectionData(
            agent_id="test_agent",
            connection_params={"type": "stdio", "command": "test"}
        )
        registry.save_connection(connection_data)
        
        # Verify the connection was saved
        saved_data = registry.get_connection("test_agent")
        assert saved_data is not None
        assert saved_data.agent_id == "test_agent"


def test_mcp_registry_load_registry():
    """Test loading registry from file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        
        # Write some initial data
        initial_data = {
            "test_agent": {
                "agent_id": "test_agent",
                "connection_params": {"type": "stdio", "command": "test"},
                "timestamp": "2023-01-01T00:00:00",
                "status": "connected",
                "last_validated": "2023-01-01T00:00:00"
            }
        }
        with open(temp_file, "w") as f:
            json.dump(initial_data, f)
        
        registry = MCPConnectionRegistry(registry_file=str(temp_file))
        loaded_data = registry.get_connection("test_agent")
        assert loaded_data is not None
        assert loaded_data.agent_id == "test_agent"
        assert loaded_data.connection_params == {"type": "stdio", "command": "test"}


def test_mcp_registry_remove_connection():
    """Test removing a connection from the registry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        
        registry = MCPConnectionRegistry(registry_file=str(temp_file))
        connection_data = MCPConnectionData(
            agent_id="test_agent_to_remove",
            connection_params={"type": "stdio", "command": "test"}
        )
        registry.save_connection(connection_data)
        
        # Verify the connection was saved
        assert registry.get_connection("test_agent_to_remove") is not None
        
        # Remove the connection
        result = registry.remove_connection("test_agent_to_remove")
        assert result is True
        
        # Verify the connection was removed
        assert registry.get_connection("test_agent_to_remove") is None


def test_mcp_registry_is_connection_valid():
    """Test the connection validation functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        
        registry = MCPConnectionRegistry(registry_file=str(temp_file))
        
        # Test with non-existent connection
        assert registry.is_connection_valid("nonexistent_agent", {}) is False
        
        # Test with valid connection
        connection_data = MCPConnectionData(
            agent_id="test_agent_valid",
            connection_params={"type": "stdio", "command": "test"}
        )
        registry.save_connection(connection_data)
        assert registry.is_connection_valid("test_agent_valid", {"type": "stdio", "command": "test"}) is True
        
        # Test with mismatched connection params
        assert registry.is_connection_valid("test_agent_valid", {"type": "http", "url": "test"}) is False


def test_mcp_registry_update_connection_timestamp():
    """Test updating connection timestamp."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        
        registry = MCPConnectionRegistry(registry_file=str(temp_file))
        connection_data = MCPConnectionData(
            agent_id="test_agent_timestamp",
            connection_params={"type": "stdio", "command": "test"}
        )
        registry.save_connection(connection_data)
        
        original_validated = registry.get_connection("test_agent_timestamp").last_validated
        
        # Wait a moment to ensure time difference
        import time
        time.sleep(0.01)
        
        # Update timestamp
        result = registry.update_connection_timestamp("test_agent_timestamp")
        assert result is True
        
        updated_validated = registry.get_connection("test_agent_timestamp").last_validated
        assert updated_validated > original_validated


def test_mcp_registry_persistence():
    """Test that saved data persists between registry instances."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        
        # Create registry and save a connection
        registry1 = MCPConnectionRegistry(registry_file=str(temp_file))
        connection_data = MCPConnectionData(
            agent_id="persistent_agent",
            connection_params={"type": "stdio", "command": "test", "args": ["arg1"]}
        )
        registry1.save_connection(connection_data)
        del registry1  # Explicitly delete to ensure data is saved to file
        
        # Create a new registry instance with the same file
        registry2 = MCPConnectionRegistry(registry_file=str(temp_file))
        
        # Verify the connection is still there
        loaded_data = registry2.get_connection("persistent_agent")
        assert loaded_data is not None
        assert loaded_data.agent_id == "persistent_agent"
        assert loaded_data.connection_params == {"type": "stdio", "command": "test", "args": ["arg1"]}


def test_mcp_registry_get_all_connections():
    """Test getting all connections from the registry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_registry.json"
        
        registry = MCPConnectionRegistry(registry_file=str(temp_file))
        
        # Add multiple connections
        connection1 = MCPConnectionData(
            agent_id="agent1",
            connection_params={"type": "stdio", "command": "test1"}
        )
        connection2 = MCPConnectionData(
            agent_id="agent2",
            connection_params={"type": "stdio", "command": "test2"}
        )
        registry.save_connection(connection1)
        registry.save_connection(connection2)
        
        # Get all connections
        all_connections = registry.get_all_connections()
        assert len(all_connections) == 2
        assert "agent1" in all_connections
        assert "agent2" in all_connections


def test_mcp_connection_data_serialization():
    """Test serialization and deserialization of MCPConnectionData."""
    original_data = {
        "agent_id": "serial_test_agent",
        "connection_params": {"type": "stdio", "command": "test", "env": {"VAR": "value"}},
        "timestamp": "2023-05-15T10:30:00",
        "status": "connected",
        "last_validated": "2023-05-15T10:35:00"
    }
    
    # Create from dict
    connection_data = MCPConnectionData.from_dict(original_data)
    
    # Convert back to dict
    serialized_data = connection_data.to_dict()
    
    # Verify the data matches
    assert serialized_data["agent_id"] == original_data["agent_id"]
    assert serialized_data["connection_params"] == original_data["connection_params"]
    assert serialized_data["status"] == original_data["status"]
    assert serialized_data["timestamp"] == original_data["timestamp"]
    assert serialized_data["last_validated"] == original_data["last_validated"]
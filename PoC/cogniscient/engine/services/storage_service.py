"""Storage Service implementation following the ringed architecture."""

import os
import json
from typing import Any, Optional
from cogniscient.engine.services.service_interface import StorageServiceInterface


class StorageServiceImpl(StorageServiceInterface):
    """Implementation of StorageService following the ringed architecture."""
    
    def __init__(self, storage_dir: str = "runtime_data"):
        """Initialize the storage service.
        
        Args:
            storage_dir: Directory to use for data persistence
        """
        self.storage_dir = storage_dir
        # Ensure the storage directory exists
        os.makedirs(storage_dir, exist_ok=True)
        
    async def initialize(self) -> bool:
        """Initialize the storage service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Ensure the storage directory exists and is accessible
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error initializing storage service: {e}")
            return False
        
    async def shutdown(self) -> bool:
        """Shutdown the storage service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # For now, there's nothing special to do on shutdown for storage
        return True

    async def save_data(self, key: str, data: Any) -> bool:
        """Save data to storage.
        
        Args:
            key: Key to store the data under
            data: Data to save
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Create a file path based on the key
            # Replace any path separators in the key to avoid directory traversal
            safe_key = key.replace("/", "_").replace("\\", "_")
            file_path = os.path.join(self.storage_dir, f"{safe_key}.json")
            
            # Write data to file
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving data with key {key}: {e}")
            return False

    async def load_data(self, key: str) -> Optional[Any]:
        """Load data from storage.
        
        Args:
            key: Key to load data from
            
        Returns:
            Loaded data if found, None otherwise
        """
        try:
            # Create a file path based on the key
            # Replace any path separators in the key to avoid directory traversal
            safe_key = key.replace("/", "_").replace("\\", "_")
            file_path = os.path.join(self.storage_dir, f"{safe_key}.json")
            
            # Check if file exists
            if not os.path.exists(file_path):
                return None
                
            # Read data from file
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data with key {key}: {e}")
            return None

    def set_runtime(self, runtime):
        """Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method for the storage service.
        """
        if not hasattr(self, 'gcs_runtime') or not self.gcs_runtime or not hasattr(self.gcs_runtime, 'mcp_service') or not self.gcs_runtime.mcp_service:
            print(f"Warning: No runtime reference for {self.__class__.__name__}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.gcs_runtime.mcp_service.mcp_client

        # Register save data tool
        save_data_tool = {
            "name": "storage_save_data",
            "description": "Save data to storage",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to store the data under"},
                    "data": {"type": "object", "description": "Data to save"}
                },
                "required": ["key", "data"]
            },
            "type": "function"
        }

        # Register load data tool
        load_data_tool = {
            "name": "storage_load_data",
            "description": "Load data from storage",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to load data from"}
                },
                "required": ["key"]
            },
            "type": "function"
        }

        # Add tools to the registry
        agent_tools = mcp_client.tool_registry.get(self.__class__.__name__, [])
        agent_tools.extend([
            save_data_tool,
            load_data_tool
        ])
        mcp_client.tool_registry[self.__class__.__name__] = agent_tools

        # Also register individual tool types
        for tool_desc in [
            save_data_tool,
            load_data_tool
        ]:
            mcp_client.tool_types[tool_desc["name"]] = True  # Is a system tool
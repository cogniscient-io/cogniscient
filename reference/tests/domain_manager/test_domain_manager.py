"""
Unit tests for the DomainManager class.

This module tests the DomainManager functionality including domain discovery,
loading, unloading, and validation.
"""
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from gcs_kernel.domain_manager import DomainManager, DomainConfig
from gcs_kernel.models import ToolDefinition


class TestDomainManager:
    """Test suite for DomainManager class"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test domains
        self.test_domains_dir = Path(tempfile.mkdtemp())
        
        # For testing, we'll temporarily change the settings
        from common.settings import settings
        self.original_domain_directory = settings.domain_directory
        settings.domain_directory = str(self.test_domains_dir)

        self.kernel_mock = MagicMock()
        
        # Mock AI orchestrator with system context builder
        self.system_context_builder_mock = MagicMock()
        self.system_context_builder_mock.prompts = {"test": "default_prompts"}
        self.system_context_builder_mock.revert_to_default_prompts.return_value = True
        self.kernel_mock.ai_orchestrator = MagicMock()
        self.kernel_mock.ai_orchestrator.system_context_builder = self.system_context_builder_mock
        
        # Mock MCP client manager
        self.mcp_client_manager_mock = MagicMock()
        self.mcp_client_manager_mock.clients = {}
        self.kernel_mock.mcp_client_manager = self.mcp_client_manager_mock
        
        # Mock registry
        self.registry_mock = MagicMock()
        self.registry_mock.tools = {}
        self.kernel_mock.registry = self.registry_mock
        
        # Create the DomainManager instance
        self.domain_manager = DomainManager(self.kernel_mock)
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Restore original domain directory setting
        from common.settings import settings
        settings.domain_directory = self.original_domain_directory
        shutil.rmtree(self.test_domains_dir)
    
    def create_test_domain(self, name, description="Test Domain", version="1.0.0", tools=None, mcp_servers=None, has_prompts=True):
        """Helper method to create a test domain with specified properties."""
        domain_path = self.test_domains_dir / name
        domain_path.mkdir(exist_ok=True)
        
        # Create metadata.json
        metadata = {
            "name": name,
            "description": description,
            "version": version
        }
        with open(domain_path / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # Create prompts.json if requested
        if has_prompts:
            prompts = {
                "system_context": {
                    "base_message_with_tools": [
                        f"Test prompts for {name} domain."
                    ]
                }
            }
            with open(domain_path / "prompts.json", "w") as f:
                json.dump(prompts, f)
        
        # Create tools.json if tools are specified
        if tools:
            tools_data = {"tools": tools}
            with open(domain_path / "tools.json", "w") as f:
                json.dump(tools_data, f)
        
        # Create mcp_servers.json if MCP servers are specified
        if mcp_servers:
            with open(domain_path / "mcp_servers.json", "w") as f:
                json.dump(mcp_servers, f)
        
        return domain_path
    
    def test_initialization(self):
        """Test DomainManager initialization."""
        assert self.domain_manager.kernel == self.kernel_mock
        assert self.domain_manager.domains_directory == self.test_domains_dir
        assert self.domain_manager.available_domains == {}
        assert self.domain_manager.current_domain is None
        assert hasattr(self.domain_manager, '_current_domain_data')
    
    def test_discover_domains(self):
        """Test discovery of available domains."""
        # Create a test domain
        self.create_test_domain("test_domain_1")
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Verify domain was discovered
        assert "test_domain_1" in self.domain_manager.available_domains
        assert self.domain_manager.available_domains["test_domain_1"] == self.test_domains_dir / "test_domain_1"
    
    def test_discover_domains_multiple(self):
        """Test discovery of multiple domains."""
        # Create multiple test domains
        self.create_test_domain("domain_1")
        self.create_test_domain("domain_2")
        self.create_test_domain("domain_3")
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Verify all domains were discovered
        assert "domain_1" in self.domain_manager.available_domains
        assert "domain_2" in self.domain_manager.available_domains
        assert "domain_3" in self.domain_manager.available_domains
        assert len(self.domain_manager.available_domains) == 3
    
    def test_discover_domains_invalid(self):
        """Test discovery with invalid domain configurations."""
        # Create a domain without metadata.json
        invalid_domain_path = self.test_domains_dir / "invalid_domain"
        invalid_domain_path.mkdir(exist_ok=True)
        
        # Create a valid domain
        self.create_test_domain("valid_domain")
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Verify only valid domain was discovered
        assert "valid_domain" in self.domain_manager.available_domains
        assert "invalid_domain" not in self.domain_manager.available_domains
    
    def test_get_available_domains(self):
        """Test getting available domains with descriptions."""
        # Create test domains
        self.create_test_domain("domain_1", description="First test domain")
        self.create_test_domain("domain_2", description="Second test domain")
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Get available domains
        available_domains = self.domain_manager.get_available_domains()
        
        # Verify domains and descriptions
        assert "domain_1" in available_domains
        assert available_domains["domain_1"] == "First test domain"
        assert "domain_2" in available_domains
        assert available_domains["domain_2"] == "Second test domain"
    
    def test_validate_domain_valid(self):
        """Test validation of a valid domain."""
        # Create a valid test domain
        self.create_test_domain("valid_domain")
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Validate the domain
        is_valid = self.domain_manager.validate_domain("valid_domain")
        
        assert is_valid is True
    
    def test_validate_domain_invalid(self):
        """Test validation of an invalid domain."""
        # Create a domain without required metadata
        invalid_domain_path = self.test_domains_dir / "invalid_domain"
        invalid_domain_path.mkdir(exist_ok=True)
        
        # Create a file instead of directory
        (self.test_domains_dir / "not_a_domain").touch()
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Validate non-existent domain
        is_valid = self.domain_manager.validate_domain("non_existent_domain")
        assert is_valid is False
        
        # Validate invalid domain
        is_valid = self.domain_manager.validate_domain("not_a_domain")
        assert is_valid is False
    
    def test_validate_domain_missing_fields(self):
        """Test validation of domain with missing required fields."""
        # Create a domain with incomplete metadata
        domain_path = self.test_domains_dir / "incomplete_domain"
        domain_path.mkdir(exist_ok=True)
        
        # Create incomplete metadata.json (missing required fields)
        metadata = {
            "name": "incomplete_domain",
            # Missing description and version
        }
        with open(domain_path / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Validate the domain
        is_valid = self.domain_manager.validate_domain("incomplete_domain")
        
        assert is_valid is False
    
    def test_load_domain_success(self):
        """Test successful domain loading."""
        # Create a test domain with tools
        test_tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                "approval_required": False
            }
        ]
        domain_path = self.create_test_domain("test_domain", tools=test_tools)
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Load the domain
        result = asyncio.run(self.domain_manager.load_domain("test_domain"))
        
        # Verify domain was loaded
        assert result is True
        assert self.domain_manager.current_domain == "test_domain"
        # Verify tools were registered
        self.kernel_mock.registry.register_tool.assert_called()
    
    def test_load_domain_invalid(self):
        """Test loading of an invalid domain."""
        # Run discovery (no domains created)
        asyncio.run(self.domain_manager.discover_domains())
        
        # Try to load non-existent domain
        result = asyncio.run(self.domain_manager.load_domain("non_existent_domain"))
        
        # Verify domain was not loaded
        assert result is False
        assert self.domain_manager.current_domain is None
    
    def test_load_domain_unloads_current(self):
        """Test that loading a new domain unloads the current one."""
        # Create two domains
        self.create_test_domain("domain_1")
        self.create_test_domain("domain_2")
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Load first domain
        result1 = asyncio.run(self.domain_manager.load_domain("domain_1"))
        assert result1 is True
        assert self.domain_manager.current_domain == "domain_1"
        
        # Load second domain (should unload first)
        result2 = asyncio.run(self.domain_manager.load_domain("domain_2"))
        assert result2 is True
        assert self.domain_manager.current_domain == "domain_2"
    
    def test_unload_domain_success(self):
        """Test successful domain unloading."""
        # Create and load a test domain
        self.create_test_domain("test_domain")
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Load the domain first
        load_result = asyncio.run(self.domain_manager.load_domain("test_domain"))
        assert load_result is True
        assert self.domain_manager.current_domain == "test_domain"
        
        # Now unload the domain
        unload_result = asyncio.run(self.domain_manager.unload_domain())
        
        # Verify domain was unloaded
        assert unload_result is True
        assert self.domain_manager.current_domain is None
    
    def test_unload_domain_no_current(self):
        """Test unloading when no domain is currently loaded."""
        # Verify no domain is currently loaded
        assert self.domain_manager.current_domain is None
        
        # Try to unload (should succeed even with no current domain)
        result = asyncio.run(self.domain_manager.unload_domain())
        
        # Verify result
        assert result is True
        assert self.domain_manager.current_domain is None
    
    def test_load_domain_with_prompts(self):
        """Test loading domain with custom prompts."""
        # Create domain with custom prompts
        domain_path = self.create_test_domain("prompt_domain")
        custom_prompts = {
            "system_context": {
                "domain_specific_info": [
                    "Custom domain-specific information."
                ]
            }
        }
        prompts_path = domain_path / "prompts.json"
        with open(prompts_path, "w") as f:
            json.dump(custom_prompts, f)
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Load the domain
        result = asyncio.run(self.domain_manager.load_domain("prompt_domain"))
        
        # Verify domain was loaded
        assert result is True
        assert self.domain_manager.current_domain == "prompt_domain"
        
        # Check that the domain data was loaded into the DomainManager
        assert self.domain_manager._current_domain_data  # Should not be empty after loading domain
    
    def test_unload_domain_reverts_prompts(self):
        """Test that unloading domain reverts to default prompts."""
        # Create domain with custom prompts
        domain_path = self.create_test_domain("prompt_domain")
        custom_prompts = {
            "system_context": {
                "domain_specific_info": [
                    "Custom domain-specific information."
                ]
            }
        }
        prompts_path = domain_path / "prompts.json"
        with open(prompts_path, "w") as f:
            json.dump(custom_prompts, f)
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Load the domain
        load_result = asyncio.run(self.domain_manager.load_domain("prompt_domain"))
        assert load_result is True
        # At this point, domain-specific prompts should be active
        
        # Now unload the domain
        unload_result = asyncio.run(self.domain_manager.unload_domain())
        assert unload_result is True
        
        # Verify that domain data was cleared
        assert self.domain_manager._current_domain_data == {}  # Should be empty after unloading domain
    
    def test_load_domain_with_mcp_servers(self):
        """Test loading domain with MCP servers."""
        # Create domain with MCP servers
        mcp_servers = [
            {
                "name": "test_server",
                "server_url": "http://localhost:8080",
                "description": "Test MCP server"
            }
        ]
        self.create_test_domain("mcp_domain", mcp_servers=mcp_servers)
        
        # Mock the connect_to_server method to return True
        self.kernel_mock.mcp_client_manager.connect_to_server = AsyncMock(return_value=True)
        
        # Run discovery
        asyncio.run(self.domain_manager.discover_domains())
        
        # Load the domain
        result = asyncio.run(self.domain_manager.load_domain("mcp_domain"))
        
        # Verify domain was loaded
        assert result is True
        assert self.domain_manager.current_domain == "mcp_domain"
        # Verify MCP server connection was attempted
        self.kernel_mock.mcp_client_manager.connect_to_server.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__])
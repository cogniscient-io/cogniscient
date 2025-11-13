"""
Unit tests for the domain tools in the GCS Kernel.

These tests validate the functionality of domain-related tools including:
- DomainListTool
- DomainLoadTool
- DomainUnloadTool
- DomainInfoTool
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from gcs_kernel.tools.domain_tools import (
    DomainListTool,
    DomainLoadTool,
    DomainUnloadTool,
    DomainInfoTool
)
from gcs_kernel.models import ToolResult


@pytest.mark.asyncio
class TestDomainListTool:
    """Test cases for the DomainListTool."""

    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.domain_manager = MagicMock()
        return kernel

    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create a DomainListTool instance for testing."""
        return DomainListTool(mock_kernel)

    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = DomainListTool(MagicMock())

        assert tool.name == "domain_list"
        assert tool.display_name == "List Domains"
        assert "List all available domains" in tool.description
        assert tool.parameters["type"] == "object"
        assert tool.parameters["required"] == []

    async def test_execute_with_no_domains(self, tool, mock_kernel):
        """Test executing the tool when no domains are available."""
        # Mock the domain manager to return an empty dict
        mock_kernel.domain_manager.get_available_domains = MagicMock(return_value={})

        result = await tool.execute({})

        assert result.tool_name == "domain_list"
        assert result.success is True
        assert "No domains are currently available" in result.llm_content
        assert result.llm_content == result.return_display

    async def test_execute_with_domains(self, tool, mock_kernel):
        """Test executing the tool when domains are available."""
        # Mock the domain manager to return some domains
        mock_domains = {
            "research": "Research and analysis domain",
            "development": "Software development domain"
        }
        mock_kernel.domain_manager.get_available_domains = MagicMock(return_value=mock_domains)
        # Mock current domain to be None (no domain loaded)
        mock_kernel.domain_manager.current_domain = None

        result = await tool.execute({})

        assert result.tool_name == "domain_list"
        assert result.success is True
        assert "Available domains:" in result.llm_content
        assert "research" in result.llm_content
        assert "development" in result.llm_content
        assert "AVAILABLE" in result.llm_content
        assert result.llm_content == result.return_display

    async def test_execute_with_loaded_domain(self, tool, mock_kernel):
        """Test executing the tool when a domain is currently loaded."""
        # Mock the domain manager to return some domains
        mock_domains = {
            "research": "Research and analysis domain"
        }
        mock_kernel.domain_manager.get_available_domains = MagicMock(return_value=mock_domains)
        # Mock current domain to be 'research' (domain loaded)
        mock_kernel.domain_manager.current_domain = "research"

        result = await tool.execute({})

        assert result.tool_name == "domain_list"
        assert result.success is True
        assert "LOADED" in result.llm_content
        assert "research" in result.llm_content
        assert result.llm_content == result.return_display

    async def test_execute_with_kernel_error(self, tool, mock_kernel):
        """Test executing the tool when kernel is not available."""
        # Mock the kernel to not have domain_manager
        kernel_without_manager = MagicMock()
        kernel_without_manager.domain_manager = None
        tool.kernel = kernel_without_manager

        result = await tool.execute({})

        assert result.tool_name == "domain_list"
        assert result.success is False
        assert "Domain manager not available" in result.error
        assert "Domain manager not available" in result.llm_content
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestDomainLoadTool:
    """Test cases for the DomainLoadTool."""

    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.domain_manager = MagicMock()
        return kernel

    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create a DomainLoadTool instance for testing."""
        return DomainLoadTool(mock_kernel)

    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = DomainLoadTool(MagicMock())

        assert tool.name == "domain_load"
        assert tool.display_name == "Load Domain"
        assert "Load a domain by its name" in tool.description
        assert tool.parameters["type"] == "object"
        assert "domain_name" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["domain_name"]

    async def test_execute_with_missing_domain_name(self, tool):
        """Test executing the tool without required domain_name parameter."""
        result = await tool.execute({})

        assert result.tool_name == "domain_load"
        assert result.success is False
        assert "Missing required parameter: domain_name" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display

    async def test_execute_with_nonexistent_domain(self, tool, mock_kernel):
        """Test executing the tool for a domain that doesn't exist."""
        # Mock available domains
        mock_kernel.domain_manager.get_available_domains = MagicMock(return_value={
            "research": "Research domain"
        })

        result = await tool.execute({"domain_name": "nonexistent_domain"})

        assert result.tool_name == "domain_load"
        assert result.success is False
        assert "does not exist" in result.error
        assert "research" in result.error  # Available domains should be listed
        assert result.error == result.llm_content
        assert result.error == result.return_display

    async def test_execute_with_successful_load(self, tool, mock_kernel):
        """Test executing the tool for a successful domain load."""
        # Mock available domains and successful load
        mock_kernel.domain_manager.get_available_domains = MagicMock(return_value={
            "research": "Research domain"
        })
        mock_kernel.domain_manager.load_domain = AsyncMock(return_value=True)

        result = await tool.execute({"domain_name": "research"})

        assert result.tool_name == "domain_load"
        assert result.success is True
        assert "Successfully loaded domain" in result.llm_content
        assert "research" in result.llm_content
        assert result.llm_content == result.return_display

    async def test_execute_with_failed_load(self, tool, mock_kernel):
        """Test executing the tool for a failed domain load."""
        # Mock available domains and failed load
        mock_kernel.domain_manager.get_available_domains = MagicMock(return_value={
            "research": "Research domain"
        })
        mock_kernel.domain_manager.load_domain = AsyncMock(return_value=False)

        result = await tool.execute({"domain_name": "research"})

        assert result.tool_name == "domain_load"
        assert result.success is False
        assert "Failed to load domain" in result.error
        assert "research" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestDomainUnloadTool:
    """Test cases for the DomainUnloadTool."""

    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.domain_manager = MagicMock()
        return kernel

    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create a DomainUnloadTool instance for testing."""
        return DomainUnloadTool(mock_kernel)

    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = DomainUnloadTool(MagicMock())

        assert tool.name == "domain_unload"
        assert tool.display_name == "Unload Domain"
        assert "Unload the currently loaded domain" in tool.description
        assert tool.parameters["type"] == "object"
        assert tool.parameters["required"] == []

    async def test_execute_with_no_domain_loaded(self, tool, mock_kernel):
        """Test executing the tool when no domain is currently loaded."""
        # Mock current domain to be None
        mock_kernel.domain_manager.current_domain = None

        result = await tool.execute({})

        assert result.tool_name == "domain_unload"
        assert result.success is True
        assert "No domain is currently loaded to unload" in result.llm_content
        assert result.llm_content == result.return_display

    async def test_execute_with_successful_unload(self, tool, mock_kernel):
        """Test executing the tool for a successful domain unload."""
        # Mock current domain to be set and successful unload
        mock_kernel.domain_manager.current_domain = "research"
        mock_kernel.domain_manager.unload_domain = AsyncMock(return_value=True)

        result = await tool.execute({})

        assert result.tool_name == "domain_unload"
        assert result.success is True
        assert "Successfully unloaded domain" in result.llm_content
        assert "research" in result.llm_content
        assert result.llm_content == result.return_display

    async def test_execute_with_failed_unload(self, tool, mock_kernel):
        """Test executing the tool for a failed domain unload."""
        # Mock current domain to be set and failed unload
        mock_kernel.domain_manager.current_domain = "research"
        mock_kernel.domain_manager.unload_domain = AsyncMock(return_value=False)

        result = await tool.execute({})

        assert result.tool_name == "domain_unload"
        assert result.success is False
        assert "Failed to unload domain" in result.error
        assert "research" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display

    async def test_execute_with_kernel_error(self, tool, mock_kernel):
        """Test executing the tool when kernel is not available."""
        # Mock the kernel to not have domain_manager
        kernel_without_manager = MagicMock()
        kernel_without_manager.domain_manager = None
        tool.kernel = kernel_without_manager

        result = await tool.execute({})

        assert result.tool_name == "domain_unload"
        assert result.success is False
        assert "Domain manager not available" in result.error
        assert "Domain manager not available" in result.llm_content
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestDomainInfoTool:
    """Test cases for the DomainInfoTool."""

    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.domain_manager = MagicMock()
        return kernel

    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create a DomainInfoTool instance for testing."""
        return DomainInfoTool(mock_kernel)

    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = DomainInfoTool(MagicMock())

        assert tool.name == "domain_info"
        assert tool.display_name == "Get Domain Info"
        assert "Get detailed information about a specific domain" in tool.description
        assert tool.parameters["type"] == "object"
        assert "domain_name" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["domain_name"]

    async def test_execute_with_missing_domain_name(self, tool):
        """Test executing the tool without required domain_name parameter."""
        result = await tool.execute({})

        assert result.tool_name == "domain_info"
        assert result.success is False
        assert "Missing required parameter: domain_name" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display

    async def test_execute_with_nonexistent_domain(self, tool, mock_kernel):
        """Test executing the tool for a domain that doesn't exist."""
        # Mock available domains
        mock_kernel.domain_manager.available_domains = {
            "research": "/path/to/research"
        }

        result = await tool.execute({"domain_name": "nonexistent_domain"})

        assert result.tool_name == "domain_info"
        assert result.success is False
        assert "does not exist" in result.error
        assert "research" in result.error  # Available domains should be listed
        assert result.error == result.llm_content
        assert result.error == result.return_display

    @patch('builtins.open', new_callable=MagicMock)
    @patch('json.load')
    async def test_execute_with_valid_domain(self, mock_json_load, mock_open, tool, mock_kernel):
        """Test executing the tool for a valid domain with metadata."""
        from pathlib import Path
        
        # Mock available domains
        mock_kernel.domain_manager.available_domains = {
            "research": Path("/path/to/research")
        }
        mock_kernel.domain_manager.current_domain = "research"  # Domain is loaded
        
        # Mock JSON metadata
        mock_json_load.return_value = {
            "name": "research",
            "description": "Research and analysis domain",
            "version": "1.0.0",
            "author": "Test Author"
        }
        
        result = await tool.execute({"domain_name": "research"})

        assert result.tool_name == "domain_info"
        assert result.success is True
        assert "Domain Information for 'research' (LOADED):" in result.llm_content
        assert "Research and analysis domain" in result.llm_content
        assert "1.0.0" in result.llm_content
        assert "Test Author" in result.llm_content
        assert result.llm_content == result.return_display

    @patch('builtins.open', side_effect=FileNotFoundError())
    async def test_execute_with_invalid_metadata(self, mock_open, tool, mock_kernel):
        """Test executing the tool when domain metadata cannot be read."""
        from pathlib import Path
        
        # Mock available domains
        mock_kernel.domain_manager.available_domains = {
            "research": Path("/path/to/research")
        }

        result = await tool.execute({"domain_name": "research"})

        assert result.tool_name == "domain_info"
        assert result.success is False
        assert "Could not read metadata" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestDomainToolsRegistration:
    """Test cases for domain tools registration function."""

    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.registry = MagicMock()
        kernel.logger = MagicMock()
        return kernel

    async def test_register_domain_tools_success(self, mock_kernel):
        """Test successful registration of all domain tools."""
        # Mock successful registration for all tools
        mock_kernel.registry.register_tool = AsyncMock(return_value=True)

        from gcs_kernel.tools.domain_tools import register_domain_tools
        success = await register_domain_tools(mock_kernel)

        assert success is True
        # Verify that register_tool was called 4 times (for the 4 domain tools)
        assert mock_kernel.registry.register_tool.call_count == 4
        assert mock_kernel.logger.info.called
        assert "Successfully registered 4 domain tools" in str(mock_kernel.logger.info.call_args)

    async def test_register_domain_tools_failure(self, mock_kernel):
        """Test failure during registration of domain tools."""
        # Mock the registry to fail on the first tool registration
        mock_kernel.registry.register_tool = AsyncMock(return_value=False)

        from gcs_kernel.tools.domain_tools import register_domain_tools
        success = await register_domain_tools(mock_kernel)

        assert success is False
        assert mock_kernel.registry.register_tool.call_count == 1  # Stops after first failure
        assert mock_kernel.logger.error.called

    async def test_register_domain_tools_no_registry(self):
        """Test domain tools registration when registry is not available."""
        # Create kernel with no registry
        kernel_without_registry = MagicMock()
        # Set the registry attribute to None to trigger the hasattr check
        kernel_without_registry.registry = None
        kernel_without_registry.logger = MagicMock()

        from gcs_kernel.tools.domain_tools import register_domain_tools
        success = await register_domain_tools(kernel_without_registry)

        assert success is False
        assert kernel_without_registry.logger.error.called
        assert "Kernel registry not available" in str(kernel_without_registry.logger.error.call_args)
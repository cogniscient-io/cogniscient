"""
Tests for UI Common Components
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from ui.common.base_ui import BaseUI, StreamingHandler, KernelAPIProtocol
from ui.common.kernel_api import KernelAPIClient
from ui.common.cli_ui import CLIUI
from gcs_kernel.kernel import GCSKernel


class MockKernelAPI(KernelAPIProtocol):
    """Mock implementation of KernelAPIProtocol for testing."""
    
    async def send_user_prompt(self, prompt: str) -> str:
        return f"Response to: {prompt}"
    
    async def stream_user_prompt(self, prompt: str):
        # This should be an async generator, not just return a string
        async def generator():
            yield f"Streaming response to: {prompt}"
        return generator()
    
    def get_kernel_status(self) -> str:
        return "Mock kernel running: True"
    
    def list_registered_tools(self) -> list:
        return ["test_tool_1", "test_tool_2"]
    
    async def get_available_tools(self):
        return {
            "test_tool_1": MagicMock(description="A test tool"),
            "test_tool_2": MagicMock(description="Another test tool")
        }
    
    async def execute_tool(self, tool_name: str, params: dict):
        return f"execution_{tool_name}"
    
    async def get_tool_result(self, execution_id: str):
        from gcs_kernel.models import ToolResult
        return ToolResult(
            tool_name="test_tool",
            llm_content="Test result content",
            return_display="Test display result",
            success=True
        )


class ConcreteBaseUIImpl(BaseUI):
    """Concrete implementation of BaseUI for testing purposes."""
    
    async def display_streaming_response(self, prompt: str) -> str:
        """Dummy implementation for testing."""
        return f"Streaming response to: {prompt}"
    
    async def display_response(self, prompt: str) -> str:
        """Dummy implementation for testing."""
        return f"Response to: {prompt}"


@pytest.mark.asyncio
class TestBaseUI:
    """Test cases for BaseUI."""
    
    async def test_base_ui_initialization(self):
        """Test BaseUI can be initialized with a kernel API."""
        mock_api = MockKernelAPI()
        base_ui = ConcreteBaseUIImpl(mock_api)
        
        assert base_ui.kernel_api is mock_api
    
    async def test_get_kernel_status(self):
        """Test getting kernel status."""
        mock_api = MockKernelAPI()
        base_ui = ConcreteBaseUIImpl(mock_api)
        
        status = base_ui.get_kernel_status()
        assert status == "Mock kernel running: True"
    
    async def test_list_tools(self):
        """Test listing tools."""
        mock_api = MockKernelAPI()
        base_ui = ConcreteBaseUIImpl(mock_api)
        
        tools = base_ui.list_tools()
        assert tools == ["test_tool_1", "test_tool_2"]


@pytest.mark.asyncio
class TestStreamingHandler:
    """Test cases for StreamingHandler."""
    
    async def test_streaming_handler_initialization(self):
        """Test StreamingHandler can be initialized."""
        handler = StreamingHandler()
        assert handler is not None
        assert hasattr(handler, '_active_tasks')
    
    async def test_handle_streaming_with_callback(self):
        """Test handling streaming with callback."""
        handler = StreamingHandler()
        
        # Create a simple async generator for testing
        async def mock_stream_generator():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        captured_chunks = []
        def callback(chunk):
            captured_chunks.append(chunk)
        
        result = await handler.handle_streaming_with_callback(
            mock_stream_generator(),
            callback
        )
        
        assert captured_chunks == ["chunk1", "chunk2", "chunk3"]
        assert result == "chunk1chunk2chunk3"


@pytest.mark.asyncio 
class TestKernelAPIClient:
    """Test cases for KernelAPIClient."""
    
    async def test_kernel_api_client_initialization(self):
        """Test KernelAPIClient can be initialized."""
        # Create a mock kernel
        mock_kernel = MagicMock()
        client = KernelAPIClient(mock_kernel)
        
        assert client.kernel is mock_kernel
    
    async def test_send_user_prompt(self):
        """Test sending a user prompt."""
        mock_kernel = AsyncMock()
        mock_kernel.submit_prompt = AsyncMock(return_value="test response")
        
        client = KernelAPIClient(mock_kernel)
        response = await client.send_user_prompt("test prompt")
        
        assert response == "test response"
        mock_kernel.submit_prompt.assert_called_once_with("test prompt")
    
    async def test_stream_user_prompt(self):
        """Test streaming a user prompt."""
        mock_kernel = MagicMock()
        mock_kernel.stream_prompt = AsyncMock()
        
        # Mock the kernel stream to yield a few values
        async def mock_stream(prompt):
            yield "chunk1"
            yield "chunk2"
        
        mock_kernel.stream_prompt = mock_stream
        client = KernelAPIClient(mock_kernel)
        
        # Test that the stream generator works
        chunks = []
        async for chunk in client.stream_user_prompt("test prompt"):
            chunks.append(chunk)
        
        assert chunks == ["chunk1", "chunk2"]
    
    async def test_get_kernel_status(self):
        """Test getting kernel status."""
        mock_kernel = MagicMock()
        mock_kernel.is_running = MagicMock(return_value=True)
        
        client = KernelAPIClient(mock_kernel)
        status = client.get_kernel_status()
        
        assert status == "Kernel running: True"
    
    async def test_list_registered_tools(self):
        """Test listing registered tools."""
        mock_registry = MagicMock()
        mock_registry.get_all_tools = MagicMock(return_value={
            "tool1": MagicMock(),
            "tool2": MagicMock()
        })
        
        mock_kernel = MagicMock()
        mock_kernel.registry = mock_registry
        
        client = KernelAPIClient(mock_kernel)
        tools = client.list_registered_tools()
        
        assert tools == ["tool1", "tool2"]
    
    async def test_get_available_tools(self):
        """Test getting available tools."""
        expected_tools = {
            "tool1": MagicMock(description="Tool 1"),
            "tool2": MagicMock(description="Tool 2")
        }
        
        mock_registry = MagicMock()
        mock_registry.get_all_tools = MagicMock(return_value=expected_tools)
        
        mock_kernel = MagicMock()
        mock_kernel.registry = mock_registry
        
        client = KernelAPIClient(mock_kernel)
        tools = await client.get_available_tools()
        
        assert tools == expected_tools


@pytest.mark.asyncio
class TestCLIUI:
    """Test cases for CLIUI."""
    
    async def test_cli_ui_initialization(self):
        """Test CLIUI can be initialized with a kernel API."""
        mock_api = MockKernelAPI()
        cli_ui = CLIUI(mock_api)
        
        assert cli_ui.kernel_api is mock_api
        assert cli_ui.streaming_handler is not None
    
    async def test_display_response(self):
        """Test displaying a non-streaming response."""
        mock_api = MockKernelAPI()
        cli_ui = CLIUI(mock_api)
        
        # Capture what would be printed
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            response = await cli_ui.display_response("test prompt")
        
        assert response == "Response to: test prompt"
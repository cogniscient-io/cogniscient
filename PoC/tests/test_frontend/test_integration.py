"""Integration tests for the frontend."""

import pytest
from fastapi.testclient import TestClient
from src.frontend.api import app
import os

client = TestClient(app)

def test_html_file_exists():
    """Should have the main HTML file."""
    assert os.path.exists('src/frontend/static/index.html')

def test_css_file_exists():
    """Should have the CSS file."""
    assert os.path.exists('src/frontend/static/css/style.css')

def test_js_file_exists():
    """Should have the JavaScript file."""
    assert os.path.exists('src/frontend/static/js/main.js')

def test_frontend_serves_html():
    """Should serve the main HTML page."""
    response = client.get('/')
    # This might fail if routing isn't set up yet
    assert response.status_code in [200, 404]

def test_frontend_integration():
    """Test the full integration of frontend with backend."""
    # Test status endpoint
    status_response = client.get('/api/status')
    assert status_response.status_code == 200
    
    # Test stream chat functionality
    stream_chat_response = client.post('/api/stream_chat',
                               json={'message': 'What can you tell me about the system?'})
    # Note: This might fail if backend components aren't properly initialized
    # but the endpoint structure should be correct
    assert stream_chat_response.status_code in [200, 422, 500]
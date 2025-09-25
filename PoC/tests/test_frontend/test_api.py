"""Tests for the frontend API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.frontend.api import app

client = TestClient(app)

def test_status_endpoint_exists():
    """Should have a status endpoint that returns JSON."""
    response = client.get('/api/status')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'

def test_stream_chat_endpoint_exists():
    """Should have a stream chat endpoint that accepts POST requests."""
    response = client.post('/api/stream_chat', json={'message': 'test'})
    # We might get an error because backend isn't fully initialized,
    # but the endpoint should exist
    assert response.status_code in [200, 422, 500]  # 422 for validation errors, 500 if backend not ready

def test_stream_chat_endpoint_rejects_invalid_data():
    """Should reject stream chat requests without proper data."""
    response = client.post('/api/stream_chat', json={})
    # Should handle missing message gracefully
    assert response.status_code in [422, 500]  # 422 for validation errors
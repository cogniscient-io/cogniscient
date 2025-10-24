# Integration Tests

This directory contains integration tests that verify the complete flow through the system, from the GCS kernel to the LLM provider and back.

## Current Integration Tests

- `test_kernel_llm_integration.py`: Tests the end-to-end flow from the kernel through to the LLM and back, using a mock provider to simulate the LLM response without requiring an actual API call.

## Running Integration Tests

To run all integration tests:

```bash
python3 -m pytest tests/integration/ -v
```

Or use the test runner script:

```bash
python3 run_integration_tests.py
```

## Test Structure

Each integration test:

1. Sets up mocked components where needed (like the MCP client)
2. Initializes the AI orchestrator service
3. Connects the orchestrator to a content generator using a mock provider
4. Sends a test request through the system
5. Verifies the response is as expected

## Mock Provider

The integration tests use a `MockProvider` that simulates LLM responses without making actual API calls. This allows the tests to run quickly and reliably without external dependencies.
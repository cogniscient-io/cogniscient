# MCP Connection Registry - Brownfield Enhancement

## Epic Goal

Implement a persistent registry to store and manage successful MCP server connections, allowing the system to cache connection information and avoid reconnection overhead on program restarts.

## Epic Description

**Existing System Context:**

- Current relevant functionality: The system currently connects to external MCP servers but doesn't persist connection information between sessions
- Technology stack: Python-based application with runtime_data directory for storing runtime information
- Integration points: Connection logic in main application with runtime_data storage

**Enhancement Details:**

- What's being added/changed: A registry system that saves successful MCP connection info to runtime_data and retrieves it on program startup
- How it integrates: The registry will store connection details (URL, status, timestamp) in a JSON file in runtime_data, with logic to check this registry before attempting new connections
- Success criteria: Reduced connection overhead, faster startup times when connections were previously established, persistent connection history

## Stories

1. **Story 1:** Implement MCP connection registry storage - Create functionality to save successful MCP connection details to runtime_data/external_agents_registry.json with connection metadata
2. **Story 2:** Implement connection registry lookup - Create functionality to check the registry for existing successful connections before attempting new connections
3. **Story 3:** Implement registry cleanup and validation - Create logic to validate registry entries and remove outdated/invalid connections

## Compatibility Requirements

- [ ] Existing MCP connection APIs remain unchanged
- [ ] Runtime data storage follows existing JSON format patterns
- [ ] UI components remain unchanged (registry is backend functionality)
- [ ] Performance impact is minimal with efficient lookup operations

## Risk Mitigation

- **Primary Risk:** Stale connection information in registry causing connection failures
- **Mitigation:** Implement validation logic to check connection status before using cached information
- **Rollback Plan:** Remove the registry file and revert to original connection logic if needed

## Example of format qwen code uses for this data
cat .qwen/settings.json
{
  "mcpServers": {
    "archon": {
      "httpUrl": "http://localhost:8051/mcp"
    }
  }
}

## Definition of Done

- [ ] All stories completed with acceptance criteria met
- [ ] Existing MCP functionality verified through testing
- [ ] Integration points working correctly
- [ ] Documentation updated appropriately
- [ ] No regression in existing features
- [ ] Registry properly creates, reads, updates, and cleans up connection information
"""Unit tests for the validator component."""

from agent_utils.validator import validate_agent_config, load_schema


def test_valid_agent_config():
    """Valid configuration should pass validation."""
    config = {
        "name": "TestAgent",
        "version": "1.0",
        "enabled": True,
        "settings": {
            "timeout": 30
        }
    }
    schema = load_schema()
    assert validate_agent_config(config, schema)


def test_invalid_agent_config_missing_required():
    """Configuration missing required fields should fail validation."""
    config = {
        "name": "TestAgent"
        # Missing version and enabled
    }
    schema = load_schema()
    assert not validate_agent_config(config, schema)
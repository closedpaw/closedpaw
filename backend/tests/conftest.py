"""
ClosedPaw Test Configuration
"""

import pytest
import asyncio
import os

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["OLLAMA_HOST"] = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def pytest_addoption(parser):
    """Add custom pytest options"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires running services)",
    )


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "security: security tests")


def pytest_collection_modifyitems(config, items):
    """Skip tests based on options"""
    skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
    skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
    
    for item in items:
        if "slow" in item.keywords and not config.getoption("--run-slow"):
            item.add_marker(skip_slow)
        if "integration" in item.keywords and not config.getoption("--run-integration"):
            item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "api_base": os.getenv("API_BASE", "http://127.0.0.1:8000"),
        "ollama_host": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        "test_model": os.getenv("TEST_MODEL", "llama3.2:3b"),
    }

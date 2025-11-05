"""Pytest configuration and fixtures for progressBarDistributed tests."""
import pytest


@pytest.fixture(autouse=True)
def cleanup_shared_memory():
    """Ensure shared memory is cleaned up after each test."""
    yield
    # Cleanup happens automatically via context managers in tests
    # This is a placeholder for any additional cleanup if needed


def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running tests"
    )
    config.addinivalue_line(
        "markers", "subprocess: marks tests that spawn subprocesses"
    )

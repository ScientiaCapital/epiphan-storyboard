"""Pytest configuration for API tests.

Ensures the ConnectorRegistry is properly initialized with all connectors
before any API tests run.
"""

import pytest

from src.connectors.registry import ConnectorRegistry


@pytest.fixture(autouse=True)
def ensure_connectors_registered():
    """Ensure all connectors are registered before each test.

    This fixture automatically runs before each test in this module
    to ensure the registry has all connectors, even if a previous test
    (like test_registry.py) called ConnectorRegistry.reset().
    """
    # Import the connectors module which triggers all @connector decorators
    # This is idempotent - decorators don't re-register if already present
    import src.connectors  # noqa: F401

    # Verify we have all expected connectors
    registry = ConnectorRegistry.get()

    # If registry was reset, re-import all connectors
    if len(registry._connectors) < 8:
        from src.connectors.close.connector import CloseConnector  # noqa: F401
        from src.connectors.fireflies.connector import FirefliesConnector  # noqa: F401
        from src.connectors.gong.connector import GongConnector  # noqa: F401
        from src.connectors.google_docs.connector import GoogleDocsConnector  # noqa: F401
        from src.connectors.linear.connector import LinearConnector  # noqa: F401
        from src.connectors.loom.connector import LoomConnector  # noqa: F401
        from src.connectors.miro.connector import MiroConnector  # noqa: F401
        from src.connectors.notion.connector import NotionConnector  # noqa: F401

        # Force re-registration
        registry.register(CloseConnector)
        registry.register(FirefliesConnector)
        registry.register(GongConnector)
        registry.register(GoogleDocsConnector)
        registry.register(LinearConnector)
        registry.register(LoomConnector)
        registry.register(MiroConnector)
        registry.register(NotionConnector)

    yield

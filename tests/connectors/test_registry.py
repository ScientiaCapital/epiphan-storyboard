"""Tests for connector registry."""

import pytest

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorStatus,
    ConnectorType,
    SyncResult,
)
from src.connectors.registry import ConnectorRegistry, connector


class TestConnectorRegistry:
    """Test ConnectorRegistry singleton and methods."""

    class MockGongConnector(BaseConnector):
        """Mock Gong connector."""

        connector_type = ConnectorType.GONG
        display_name = "Mock Gong"
        description = "Mock Gong connector"
        auth_type = AuthType.OAUTH2

        async def test_connection(self, instance: ConnectorInstance) -> bool:
            return True

        async def sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

        async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

    class MockLinearConnector(BaseConnector):
        """Mock Linear connector."""

        connector_type = ConnectorType.LINEAR
        display_name = "Mock Linear"
        description = "Mock Linear connector"
        auth_type = AuthType.API_KEY

        async def test_connection(self, instance: ConnectorInstance) -> bool:
            return True

        async def sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

        async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

    def setup_method(self):
        """Reset registry before each test."""
        ConnectorRegistry.reset()

    def teardown_method(self):
        """Reset registry after each test."""
        ConnectorRegistry.reset()

    def test_singleton_pattern(self):
        """Test registry uses singleton pattern."""
        registry1 = ConnectorRegistry.get()
        registry2 = ConnectorRegistry.get()
        assert registry1 is registry2

    def test_reset(self):
        """Test reset clears instance and connectors."""
        registry1 = ConnectorRegistry.get()
        registry1.register(self.MockGongConnector)
        assert registry1.is_registered(ConnectorType.GONG)

        ConnectorRegistry.reset()

        registry2 = ConnectorRegistry.get()
        assert registry2 is not registry1
        assert not registry2.is_registered(ConnectorType.GONG)

    def test_register(self):
        """Test registering a connector."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)
        assert registry.is_registered(ConnectorType.GONG)

    def test_register_multiple(self):
        """Test registering multiple connectors."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)
        registry.register(self.MockLinearConnector)
        assert registry.is_registered(ConnectorType.GONG)
        assert registry.is_registered(ConnectorType.LINEAR)

    def test_register_missing_connector_type(self):
        """Test registering class without connector_type raises error."""

        class InvalidConnector(BaseConnector):
            display_name = "Invalid"
            description = "Invalid"
            auth_type = AuthType.API_KEY

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return True

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

        registry = ConnectorRegistry.get()
        with pytest.raises(ValueError, match="must define connector_type"):
            registry.register(InvalidConnector)

    def test_get_connector_by_enum(self):
        """Test getting connector by ConnectorType enum."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)

        connector = registry.get_connector(ConnectorType.GONG)
        assert isinstance(connector, self.MockGongConnector)
        assert connector.connector_type == ConnectorType.GONG

    def test_get_connector_by_string(self):
        """Test getting connector by string value."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)

        connector = registry.get_connector("gong")
        assert isinstance(connector, self.MockGongConnector)
        assert connector.connector_type == ConnectorType.GONG

    def test_get_connector_returns_new_instance(self):
        """Test get_connector returns new instance each time."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)

        connector1 = registry.get_connector(ConnectorType.GONG)
        connector2 = registry.get_connector(ConnectorType.GONG)
        assert connector1 is not connector2

    def test_get_connector_unknown_type(self):
        """Test getting unknown connector raises error."""
        registry = ConnectorRegistry.get()
        with pytest.raises(ValueError, match="Unknown connector type"):
            registry.get_connector(ConnectorType.GONG)

    def test_get_connector_invalid_string(self):
        """Test getting connector with invalid string raises error."""
        registry = ConnectorRegistry.get()
        with pytest.raises(ValueError):
            registry.get_connector("invalid_type")

    def test_is_registered_enum_true(self):
        """Test is_registered with registered enum."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)
        assert registry.is_registered(ConnectorType.GONG)

    def test_is_registered_enum_false(self):
        """Test is_registered with unregistered enum."""
        registry = ConnectorRegistry.get()
        assert not registry.is_registered(ConnectorType.GONG)

    def test_is_registered_string_true(self):
        """Test is_registered with registered string."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)
        assert registry.is_registered("gong")

    def test_is_registered_string_false(self):
        """Test is_registered with unregistered string."""
        registry = ConnectorRegistry.get()
        assert not registry.is_registered("gong")

    def test_is_registered_invalid_string(self):
        """Test is_registered with invalid string."""
        registry = ConnectorRegistry.get()
        assert not registry.is_registered("invalid_type")

    def test_list_available_empty(self):
        """Test list_available with no connectors."""
        registry = ConnectorRegistry.get()
        connectors = registry.list_available()
        assert connectors == []

    def test_list_available_single(self):
        """Test list_available with one connector."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)

        connectors = registry.list_available()
        assert len(connectors) == 1
        assert connectors[0]["type"] == "gong"
        assert connectors[0]["display_name"] == "Mock Gong"
        assert connectors[0]["auth_type"] == "oauth2"

    def test_list_available_multiple_sorted(self):
        """Test list_available with multiple connectors is sorted."""
        registry = ConnectorRegistry.get()
        # Register in reverse order
        registry.register(self.MockLinearConnector)
        registry.register(self.MockGongConnector)

        connectors = registry.list_available()
        assert len(connectors) == 2
        # Should be sorted by type value
        assert connectors[0]["type"] == "gong"  # comes before "linear"
        assert connectors[1]["type"] == "linear"

    def test_list_available_returns_metadata(self):
        """Test list_available returns full metadata."""
        registry = ConnectorRegistry.get()
        registry.register(self.MockGongConnector)

        connectors = registry.list_available()
        assert connectors[0] == {
            "type": "gong",
            "display_name": "Mock Gong",
            "description": "Mock Gong connector",
            "auth_type": "oauth2",
            "supports_webhook": False,
            "required_config_fields": [],
        }


class TestConnectorDecorator:
    """Test @connector decorator."""

    def setup_method(self):
        """Reset registry before each test."""
        ConnectorRegistry.reset()

    def teardown_method(self):
        """Reset registry after each test."""
        ConnectorRegistry.reset()

    def test_decorator_registers_connector(self):
        """Test @connector decorator registers the class."""

        @connector
        class DecoratedConnector(BaseConnector):
            connector_type = ConnectorType.GONG
            display_name = "Decorated"
            description = "Decorated connector"
            auth_type = AuthType.API_KEY

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return True

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

        registry = ConnectorRegistry.get()
        assert registry.is_registered(ConnectorType.GONG)

    def test_decorator_returns_class(self):
        """Test @connector decorator returns the same class."""

        @connector
        class DecoratedConnector(BaseConnector):
            connector_type = ConnectorType.GONG
            display_name = "Decorated"
            description = "Decorated connector"
            auth_type = AuthType.API_KEY

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return True

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

        # Should be able to instantiate directly
        instance = DecoratedConnector()
        assert instance.connector_type == ConnectorType.GONG

    def test_decorator_allows_retrieval(self):
        """Test decorated connector can be retrieved from registry."""

        @connector
        class DecoratedConnector(BaseConnector):
            connector_type = ConnectorType.GONG
            display_name = "Decorated"
            description = "Decorated connector"
            auth_type = AuthType.API_KEY

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return True

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

        registry = ConnectorRegistry.get()
        retrieved = registry.get_connector(ConnectorType.GONG)
        assert isinstance(retrieved, DecoratedConnector)

    def test_multiple_decorated_connectors(self):
        """Test multiple @connector decorators work together."""

        @connector
        class GongConnector(BaseConnector):
            connector_type = ConnectorType.GONG
            display_name = "Gong"
            description = "Gong connector"
            auth_type = AuthType.OAUTH2

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return True

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

        @connector
        class LinearConnector(BaseConnector):
            connector_type = ConnectorType.LINEAR
            display_name = "Linear"
            description = "Linear connector"
            auth_type = AuthType.API_KEY

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return True

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

        registry = ConnectorRegistry.get()
        assert registry.is_registered(ConnectorType.GONG)
        assert registry.is_registered(ConnectorType.LINEAR)

        connectors = registry.list_available()
        assert len(connectors) == 2


class TestRegistryIntegration:
    """Integration tests for registry with multiple operations."""

    def setup_method(self):
        """Reset registry before each test."""
        ConnectorRegistry.reset()

    def teardown_method(self):
        """Reset registry after each test."""
        ConnectorRegistry.reset()

    @pytest.mark.asyncio
    async def test_register_retrieve_execute(self):
        """Test full flow: register, retrieve, execute."""

        @connector
        class TestConnector(BaseConnector):
            connector_type = ConnectorType.GONG
            display_name = "Test"
            description = "Test connector"
            auth_type = AuthType.API_KEY

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return instance.config.get("valid", False)

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True, items_fetched=10)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True, items_fetched=100)

        # Register (already done by decorator)
        registry = ConnectorRegistry.get()
        assert registry.is_registered(ConnectorType.GONG)

        # Retrieve
        conn = registry.get_connector(ConnectorType.GONG)

        # Execute
        instance = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
            config={"valid": True},
        )

        assert await conn.test_connection(instance) is True
        sync_result = await conn.sync(instance)
        assert sync_result.success is True
        assert sync_result.items_fetched == 10

        full_sync_result = await conn.full_sync(instance)
        assert full_sync_result.success is True
        assert full_sync_result.items_fetched == 100

    def test_registry_isolation_between_resets(self):
        """Test registry properly isolates state between resets."""
        registry1 = ConnectorRegistry.get()

        @connector
        class Connector1(BaseConnector):
            connector_type = ConnectorType.GONG
            display_name = "First"
            description = "First"
            auth_type = AuthType.API_KEY

            async def test_connection(self, instance: ConnectorInstance) -> bool:
                return True

            async def sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

            async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
                return SyncResult(success=True)

        assert len(registry1.list_available()) == 1

        # Reset and verify clean state
        ConnectorRegistry.reset()
        registry2 = ConnectorRegistry.get()
        assert len(registry2.list_available()) == 0

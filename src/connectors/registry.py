"""Connector registry for discovering and managing connectors."""

from src.connectors.base import BaseConnector, ConnectorType


class ConnectorRegistry:
    """Registry of available connectors.

    Singleton registry that manages all registered connector classes.
    Connectors can be registered manually or via the @connector decorator.

    Example:
        from src.connectors import ConnectorRegistry, connector

        @connector
        class MyConnector(BaseConnector):
            connector_type = ConnectorType.GONG
            ...

        registry = ConnectorRegistry.get()
        gong = registry.get_connector(ConnectorType.GONG)
    """

    _instance: "ConnectorRegistry | None" = None
    _connectors: dict[ConnectorType, type[BaseConnector]] = {}

    @classmethod
    def get(cls) -> "ConnectorRegistry":
        """Get singleton instance.

        Returns:
            The global ConnectorRegistry instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset registry (for testing).

        Clears the singleton instance and all registered connectors.
        """
        cls._instance = None
        cls._connectors = {}

    def register(self, connector_class: type[BaseConnector]) -> None:
        """Register a connector class.

        Args:
            connector_class: Connector class to register

        Raises:
            ValueError: If connector_type is not defined on the class
        """
        if not hasattr(connector_class, "connector_type"):
            raise ValueError(
                f"Connector class {connector_class.__name__} must define connector_type"
            )
        self._connectors[connector_class.connector_type] = connector_class

    def get_connector(self, connector_type: ConnectorType | str) -> BaseConnector:
        """Get connector instance by type.

        Args:
            connector_type: ConnectorType enum or string value

        Returns:
            New instance of the connector class

        Raises:
            ValueError: If connector type is unknown
        """
        if isinstance(connector_type, str):
            connector_type = ConnectorType(connector_type)
        if connector_type not in self._connectors:
            raise ValueError(f"Unknown connector type: {connector_type}")
        return self._connectors[connector_type]()

    def list_available(self) -> list[dict]:
        """List all registered connectors.

        Returns:
            List of connector metadata dicts, sorted by type
        """
        return [
            self._connectors[ct]().to_dict()
            for ct in sorted(self._connectors.keys(), key=lambda x: x.value)
        ]

    def is_registered(self, connector_type: ConnectorType | str) -> bool:
        """Check if connector is registered.

        Args:
            connector_type: ConnectorType enum or string value

        Returns:
            True if connector is registered
        """
        if isinstance(connector_type, str):
            try:
                connector_type = ConnectorType(connector_type)
            except ValueError:
                return False
        return connector_type in self._connectors


def connector(cls: type[BaseConnector]) -> type[BaseConnector]:
    """Decorator to auto-register a connector class.

    Example:
        @connector
        class GongConnector(BaseConnector):
            connector_type = ConnectorType.GONG
            ...

    Args:
        cls: Connector class to register

    Returns:
        The same class (allows use as decorator)
    """
    ConnectorRegistry.get().register(cls)
    return cls

"""Plugin registry and loader for conductor-ai SDK.

Provides:
- PluginRegistry: Isolated registry for plugin tools (doesn't pollute global)
- PluginLoader: Auto-discover and load plugins from directories or packages

Usage:
    # In your plugin's __init__.py
    from conductor_ai.sdk import BaseTool, PluginRegistry

    registry = PluginRegistry()

    @registry.tool
    class MyTool(BaseTool):
        ...

    def register(global_registry):
        '''Called by PluginLoader to register all tools.'''
        for tool in registry.tools:
            global_registry.register(tool)

    # Or in your main app
    from conductor_ai.sdk import PluginLoader
    from src.tools.registry import ToolRegistry

    loader = PluginLoader()
    global_registry = ToolRegistry()

    # Load all plugins from a directory
    loader.load_from_directory("plugins/", global_registry)

    # Or load a specific package
    loader.load_from_package("my_plugin_package", global_registry)
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.tools.base import BaseTool
    from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Isolated registry for plugin tools.

    Unlike the global ToolRegistry singleton, PluginRegistry creates an
    isolated instance that plugins can use to register their tools before
    merging into the global registry.

    This prevents plugin loading order issues and allows plugins to be
    loaded/unloaded without affecting other plugins.
    """

    def __init__(self) -> None:
        """Initialize an empty plugin registry."""
        self._tools: list[BaseTool] = []

    def register(self, tool: BaseTool) -> None:
        """Register a tool in this plugin registry.

        Args:
            tool: The tool instance to register
        """
        self._tools.append(tool)

    def tool(self, tool_class: type[BaseTool]) -> type[BaseTool]:
        """Decorator to register a tool class.

        Usage:
            @registry.tool
            class MyTool(BaseTool):
                ...

        Args:
            tool_class: The tool class to instantiate and register

        Returns:
            The same tool class (for chaining)
        """
        tool_instance = tool_class()
        self.register(tool_instance)
        return tool_class

    @property
    def tools(self) -> list[BaseTool]:
        """Get all registered tools.

        Returns:
            List of registered tool instances
        """
        return self._tools.copy()

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


class PluginLoader:
    """Loader for discovering and loading conductor-ai plugins.

    Plugins can be loaded from:
    - A directory containing plugin packages
    - An installed pip package

    Each plugin must have a `register(registry)` function in its __init__.py
    that accepts a ToolRegistry and registers its tools.
    """

    def __init__(self) -> None:
        """Initialize the plugin loader."""
        self._loaded_plugins: set[str] = set()

    def load_from_directory(
        self,
        plugin_dir: str | Path,
        global_registry: ToolRegistry,
    ) -> list[str]:
        """Load all plugins from a directory.

        Each subdirectory containing an __init__.py is treated as a plugin.
        The plugin must have a `register(registry)` function.

        Args:
            plugin_dir: Path to directory containing plugin packages
            global_registry: The global ToolRegistry to register tools into

        Returns:
            List of loaded plugin names

        Raises:
            FileNotFoundError: If plugin_dir doesn't exist
        """
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            raise FileNotFoundError(f"Plugin directory not found: {plugin_dir}")

        loaded = []

        for item in plugin_path.iterdir():
            if not item.is_dir():
                continue

            init_file = item / "__init__.py"
            if not init_file.exists():
                logger.debug(f"Skipping {item.name}: no __init__.py")
                continue

            try:
                plugin_name = self._load_plugin_from_path(item, global_registry)
                if plugin_name:
                    loaded.append(plugin_name)
            except Exception as e:
                logger.error(f"Failed to load plugin {item.name}: {e}")
                continue

        return loaded

    def load_from_package(
        self,
        package_name: str,
        global_registry: ToolRegistry,
    ) -> None:
        """Load a plugin from an installed pip package.

        The package must have a `register(registry)` function.

        Args:
            package_name: Name of the pip package to load
            global_registry: The global ToolRegistry to register tools into

        Raises:
            ImportError: If package not found or missing register function
        """
        if package_name in self._loaded_plugins:
            logger.debug(f"Plugin {package_name} already loaded")
            return

        try:
            module = importlib.import_module(package_name)
        except ImportError as e:
            raise ImportError(f"Cannot import plugin package '{package_name}': {e}")

        register_fn = getattr(module, "register", None)
        if register_fn is None:
            raise ImportError(
                f"Plugin package '{package_name}' missing 'register(registry)' function"
            )

        if not callable(register_fn):
            raise ImportError(
                f"Plugin '{package_name}' has 'register' but it's not callable"
            )

        # Call the register function
        register_fn(global_registry)
        self._loaded_plugins.add(package_name)
        logger.info(f"Loaded plugin package: {package_name}")

    def _load_plugin_from_path(
        self,
        plugin_path: Path,
        global_registry: ToolRegistry,
    ) -> str | None:
        """Load a single plugin from a directory path.

        Args:
            plugin_path: Path to the plugin directory
            global_registry: Registry to register tools into

        Returns:
            Plugin name if loaded successfully, None otherwise
        """
        plugin_name = plugin_path.name

        if plugin_name in self._loaded_plugins:
            logger.debug(f"Plugin {plugin_name} already loaded")
            return None

        # Load the module from path
        spec = importlib.util.spec_from_file_location(
            plugin_name,
            plugin_path / "__init__.py",
        )
        if spec is None or spec.loader is None:
            logger.warning(f"Cannot create module spec for {plugin_name}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Error executing plugin module {plugin_name}: {e}")
            del sys.modules[plugin_name]
            return None

        # Look for register function
        register_fn = getattr(module, "register", None)
        if register_fn is None:
            logger.warning(
                f"Plugin {plugin_name} missing 'register(registry)' function"
            )
            return None

        if not callable(register_fn):
            logger.warning(f"Plugin {plugin_name} has 'register' but not callable")
            return None

        # Call register to add tools
        try:
            register_fn(global_registry)
        except Exception as e:
            logger.error(f"Error calling register() in {plugin_name}: {e}")
            return None

        self._loaded_plugins.add(plugin_name)
        logger.info(f"Loaded plugin: {plugin_name}")
        return plugin_name

    @property
    def loaded_plugins(self) -> set[str]:
        """Get the set of loaded plugin names.

        Returns:
            Set of plugin names that have been loaded
        """
        return self._loaded_plugins.copy()

    def is_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is already loaded.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if loaded, False otherwise
        """
        return plugin_name in self._loaded_plugins

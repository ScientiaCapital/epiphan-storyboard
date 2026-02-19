"""Tests for the code_run tool."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.tools.base import ToolCategory, ToolResult
from src.tools.code_run import CodeRunTool


@pytest.fixture
def code_run_tool():
    """Create a CodeRunTool instance for testing."""
    return CodeRunTool()


class TestCodeRunToolDefinition:
    """Test the tool definition and schema."""

    def test_tool_name(self, code_run_tool):
        """Test that the tool has the correct name."""
        assert code_run_tool.definition.name == "code_run"

    def test_tool_category(self, code_run_tool):
        """Test that the tool is in the CODE category."""
        assert code_run_tool.definition.category == ToolCategory.CODE

    def test_requires_approval(self, code_run_tool):
        """Test that the tool does not require approval (sandboxed execution is safe)."""
        assert code_run_tool.definition.requires_approval is False

    def test_parameters_schema(self, code_run_tool):
        """Test that the parameters schema is correctly defined."""
        params = code_run_tool.definition.parameters
        assert params["type"] == "object"
        assert set(params["required"]) == {"code", "language"}
        assert "code" in params["properties"]
        assert "language" in params["properties"]
        assert "timeout" in params["properties"]

    def test_language_enum(self, code_run_tool):
        """Test that language parameter has correct enum values."""
        params = code_run_tool.definition.parameters
        assert params["properties"]["language"]["enum"] == ["python", "javascript"]

    def test_timeout_constraints(self, code_run_tool):
        """Test that timeout parameter has correct constraints."""
        params = code_run_tool.definition.parameters
        timeout_props = params["properties"]["timeout"]
        assert timeout_props["minimum"] == 1
        assert timeout_props["maximum"] == 60
        assert timeout_props["default"] == 30

    def test_llm_schema(self, code_run_tool):
        """Test that the LLM schema is correctly formatted."""
        schema = code_run_tool.get_llm_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "code_run"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]


class TestArgumentValidation:
    """Test argument validation."""

    @pytest.mark.asyncio
    async def test_missing_code_parameter(self, code_run_tool):
        """Test error when code parameter is missing."""
        result = await code_run_tool.run({"language": "python"})
        assert result.success is False
        assert "Code parameter is required" in result.error

    @pytest.mark.asyncio
    async def test_empty_code_parameter(self, code_run_tool):
        """Test error when code parameter is empty or whitespace only."""
        result = await code_run_tool.run({"code": "   ", "language": "python"})
        assert result.success is False
        assert "Code parameter is required and cannot be empty" in result.error

    @pytest.mark.asyncio
    async def test_missing_language_parameter(self, code_run_tool):
        """Test error when language parameter is missing."""
        result = await code_run_tool.run({"code": "print('hello')"})
        assert result.success is False
        assert "Invalid language" in result.error

    @pytest.mark.asyncio
    async def test_invalid_language(self, code_run_tool):
        """Test error when language is invalid."""
        result = await code_run_tool.run({
            "code": "echo 'hello'",
            "language": "bash",
        })
        assert result.success is False
        assert "Invalid language" in result.error
        assert "bash" in result.error

    @pytest.mark.asyncio
    async def test_timeout_too_low(self, code_run_tool):
        """Test error when timeout is below minimum."""
        result = await code_run_tool.run({
            "code": "print('hello')",
            "language": "python",
            "timeout": 0,
        })
        assert result.success is False
        assert "Timeout must be an integer between 1 and 60" in result.error

    @pytest.mark.asyncio
    async def test_timeout_too_high(self, code_run_tool):
        """Test error when timeout exceeds maximum."""
        result = await code_run_tool.run({
            "code": "print('hello')",
            "language": "python",
            "timeout": 120,
        })
        assert result.success is False
        assert "Timeout must be an integer between 1 and 60" in result.error

    @pytest.mark.asyncio
    async def test_timeout_not_integer(self, code_run_tool):
        """Test error when timeout is not an integer."""
        result = await code_run_tool.run({
            "code": "print('hello')",
            "language": "python",
            "timeout": "30",
        })
        assert result.success is False
        assert "Timeout must be an integer" in result.error


class TestSubprocessExecution:
    """Test subprocess execution (fallback mode)."""

    @pytest.mark.asyncio
    async def test_python_hello_world(self, code_run_tool):
        """Test executing simple Python code via subprocess."""
        # Force subprocess mode
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "print('Hello, World!')",
            "language": "python",
        })

        assert result.success is True
        assert result.result["stdout"].strip() == "Hello, World!"
        assert result.result["stderr"] == ""
        assert result.result["exit_code"] == 0
        assert result.result["execution_method"] == "subprocess"
        assert result.result["language"] == "python"

    @pytest.mark.asyncio
    async def test_python_calculation(self, code_run_tool):
        """Test Python code that performs a calculation."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "print(2 + 2)",
            "language": "python",
        })

        assert result.success is True
        assert result.result["stdout"].strip() == "4"
        assert result.result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_python_error(self, code_run_tool):
        """Test Python code that raises an error."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "raise ValueError('test error')",
            "language": "python",
        })

        assert result.success is True  # Execution succeeded, code failed
        assert result.result["exit_code"] != 0
        assert "ValueError" in result.result["stderr"]
        assert "test error" in result.result["stderr"]

    @pytest.mark.asyncio
    async def test_python_syntax_error(self, code_run_tool):
        """Test Python code with syntax error."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "print('unclosed string",
            "language": "python",
        })

        assert result.success is True  # Execution succeeded, code failed
        assert result.result["exit_code"] != 0
        assert "SyntaxError" in result.result["stderr"] or "error" in result.result["stderr"].lower()

    @pytest.mark.asyncio
    async def test_javascript_hello_world(self, code_run_tool):
        """Test executing simple JavaScript code via subprocess."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "console.log('Hello, World!')",
            "language": "javascript",
        })

        assert result.success is True
        assert result.result["stdout"].strip() == "Hello, World!"
        assert result.result["stderr"] == ""
        assert result.result["exit_code"] == 0
        assert result.result["execution_method"] == "subprocess"
        assert result.result["language"] == "javascript"

    @pytest.mark.asyncio
    async def test_javascript_calculation(self, code_run_tool):
        """Test JavaScript code that performs a calculation."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "console.log(2 + 2)",
            "language": "javascript",
        })

        assert result.success is True
        assert result.result["stdout"].strip() == "4"
        assert result.result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_javascript_error(self, code_run_tool):
        """Test JavaScript code that throws an error."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "throw new Error('test error')",
            "language": "javascript",
        })

        assert result.success is True  # Execution succeeded, code failed
        assert result.result["exit_code"] != 0
        assert "Error" in result.result["stderr"]

    @pytest.mark.asyncio
    async def test_subprocess_timeout(self, code_run_tool):
        """Test timeout handling in subprocess mode."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        # Code that sleeps longer than timeout
        result = await code_run_tool.run({
            "code": "import time; time.sleep(10)",
            "language": "python",
            "timeout": 1,
        })

        assert result.success is True
        assert result.result["exit_code"] == 124  # Timeout exit code
        assert "timed out" in result.result["stderr"].lower()

    @pytest.mark.asyncio
    async def test_subprocess_stdout_stderr_capture(self, code_run_tool):
        """Test that both stdout and stderr are captured."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool.run({
            "code": "import sys; print('stdout'); print('stderr', file=sys.stderr)",
            "language": "python",
        })

        assert result.success is True
        assert "stdout" in result.result["stdout"]
        assert "stderr" in result.result["stderr"]


class TestDockerExecution:
    """Test Docker-based execution."""

    @pytest.mark.asyncio
    async def test_docker_python_execution(self, code_run_tool):
        """Test Python execution via Docker."""
        # Mock Docker client
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        # Docker logs() returns combined stdout/stderr as bytes
        mock_container.logs.return_value = b"Hello from Docker\n"
        mock_container.remove.return_value = None

        mock_client.images.pull.return_value = None
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True

        # Patch at the module level where it's used
        tool = CodeRunTool()
        tool._docker_client = mock_client
        tool._docker_checked = True

        with patch("src.tools.code_run.DOCKER_AVAILABLE", True):
            result = await tool.run({
                "code": "print('Hello from Docker')",
                "language": "python",
            })

            assert result.success is True
            assert result.result["stdout"].strip() == "Hello from Docker"
            assert result.result["exit_code"] == 0
            assert result.result["execution_method"] == "docker"

    @pytest.mark.asyncio
    async def test_docker_javascript_execution(self, code_run_tool):
        """Test JavaScript execution via Docker."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"42\n"
        mock_container.remove.return_value = None

        mock_client.images.pull.return_value = None
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True

        tool = CodeRunTool()
        tool._docker_client = mock_client
        tool._docker_checked = True

        with patch("src.tools.code_run.DOCKER_AVAILABLE", True):
            result = await tool.run({
                "code": "console.log(42)",
                "language": "javascript",
            })

            assert result.success is True
            assert result.result["stdout"].strip() == "42"
            assert result.result["execution_method"] == "docker"

    @pytest.mark.asyncio
    async def test_docker_timeout_handling(self, code_run_tool):
        """Test timeout handling in Docker mode."""
        mock_client = MagicMock()
        mock_container = MagicMock()

        # Simulate timeout - make wait() block for longer than timeout
        def blocking_wait(timeout):
            # Return a coroutine that will timeout
            import time
            time.sleep(timeout + 1)
            return {"StatusCode": 0}

        mock_container.wait = blocking_wait
        mock_container.kill.return_value = None
        mock_container.remove.return_value = None

        mock_client.images.pull.return_value = None
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True

        tool = CodeRunTool()
        tool._docker_client = mock_client
        tool._docker_checked = True

        with patch("src.tools.code_run.DOCKER_AVAILABLE", True):
            result = await tool.run({
                "code": "import time; time.sleep(100)",
                "language": "python",
                "timeout": 1,
            })

            assert result.success is True
            assert result.result["exit_code"] == 124
            assert "timed out" in result.result["stderr"].lower()

    @pytest.mark.asyncio
    async def test_docker_security_parameters(self, code_run_tool):
        """Test that Docker containers are created with security restrictions."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"ok\n"
        mock_container.remove.return_value = None

        mock_client.images.pull.return_value = None
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True

        tool = CodeRunTool()
        tool._docker_client = mock_client
        tool._docker_checked = True

        with patch("src.tools.code_run.DOCKER_AVAILABLE", True):
            await tool.run({
                "code": "print('test')",
                "language": "python",
            })

            # Check that containers.run was called with security parameters
            call_kwargs = mock_client.containers.run.call_args[1]
            assert call_kwargs["network_mode"] == "none"
            assert call_kwargs["mem_limit"] == "128m"
            assert call_kwargs["read_only"] is True
            assert "/tmp" in call_kwargs["tmpfs"]

    @pytest.mark.asyncio
    async def test_docker_unavailable_fallback(self, code_run_tool):
        """Test fallback to subprocess when Docker is unavailable."""
        with patch("src.tools.code_run.DOCKER_AVAILABLE", False):
            tool = CodeRunTool()

            result = await tool.run({
                "code": "print('fallback test')",
                "language": "python",
            })

            assert result.success is True
            assert result.result["execution_method"] == "subprocess"


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_unexpected_error_in_execution(self, code_run_tool):
        """Test handling of unexpected errors during execution."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        # Mock subprocess to raise an unexpected error
        with patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("Unexpected error")):
            result = await code_run_tool.run({
                "code": "print('test')",
                "language": "python",
            })

            assert result.success is False
            assert "Subprocess execution failed" in result.error

    @pytest.mark.asyncio
    async def test_python_not_found(self, code_run_tool):
        """Test error when Python interpreter is not found."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            result = await code_run_tool.run({
                "code": "print('test')",
                "language": "python",
            })

            assert result.success is False
            assert "Python interpreter not found" in result.error

    @pytest.mark.asyncio
    async def test_node_not_found(self, code_run_tool):
        """Test error when Node.js interpreter is not found."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            result = await code_run_tool.run({
                "code": "console.log('test')",
                "language": "javascript",
            })

            assert result.success is False
            assert "Node.js interpreter not found" in result.error


class TestExecutionTiming:
    """Test execution timing functionality."""

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self, code_run_tool):
        """Test that execution time is recorded."""
        code_run_tool._docker_checked = True
        code_run_tool._docker_client = None

        result = await code_run_tool._execute_with_timing({
            "code": "print('test')",
            "language": "python",
        })

        assert isinstance(result, ToolResult)
        assert result.execution_time_ms >= 0
        # Should complete quickly
        assert result.execution_time_ms < 10000  # Less than 10 seconds

    @pytest.mark.asyncio
    async def test_execution_time_on_error(self, code_run_tool):
        """Test that execution time is recorded even on error."""
        result = await code_run_tool._execute_with_timing({
            "code": "print('test')",
            "language": "invalid",
        })

        assert result.success is False
        assert result.execution_time_ms >= 0


class TestDockerAvailabilityCheck:
    """Test Docker availability checking."""

    def test_docker_available_when_installed(self, code_run_tool):
        """Test Docker availability check when Docker is installed."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # Directly inject the mock docker module
        import src.tools.code_run as cr
        original_docker = getattr(cr, 'docker', None)

        try:
            # Create a fake docker module
            mock_docker = MagicMock()
            mock_docker.from_env.return_value = mock_client
            cr.docker = mock_docker

            with patch("src.tools.code_run.DOCKER_AVAILABLE", True):
                # Reset state
                code_run_tool._docker_checked = False
                code_run_tool._docker_client = None

                assert code_run_tool._check_docker_available() is True
                assert code_run_tool._docker_client is not None
        finally:
            # Restore original
            if original_docker is None and hasattr(cr, 'docker'):
                delattr(cr, 'docker')
            elif original_docker is not None:
                cr.docker = original_docker

    def test_docker_unavailable_when_not_installed(self, code_run_tool):
        """Test Docker availability check when Docker is not installed."""
        with patch("src.tools.code_run.DOCKER_AVAILABLE", False):
            assert code_run_tool._check_docker_available() is False
            assert code_run_tool._docker_client is None

    def test_docker_unavailable_when_ping_fails(self, code_run_tool):
        """Test Docker availability check when Docker daemon is not running."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Cannot connect to Docker daemon")

        # Directly inject the mock docker module
        import src.tools.code_run as cr
        original_docker = getattr(cr, 'docker', None)

        try:
            # Create a fake docker module
            mock_docker = MagicMock()
            mock_docker.from_env.return_value = mock_client
            cr.docker = mock_docker

            with patch("src.tools.code_run.DOCKER_AVAILABLE", True):
                # Reset state
                code_run_tool._docker_checked = False
                code_run_tool._docker_client = None

                assert code_run_tool._check_docker_available() is False
                assert code_run_tool._docker_client is None
        finally:
            # Restore original
            if original_docker is None and hasattr(cr, 'docker'):
                delattr(cr, 'docker')
            elif original_docker is not None:
                cr.docker = original_docker

    def test_docker_check_cached(self, code_run_tool):
        """Test that Docker availability check is cached."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # Directly inject the mock docker module
        import src.tools.code_run as cr
        original_docker = getattr(cr, 'docker', None)

        try:
            # Create a fake docker module
            mock_docker = MagicMock()
            mock_docker.from_env.return_value = mock_client
            cr.docker = mock_docker

            with patch("src.tools.code_run.DOCKER_AVAILABLE", True):
                # Reset state
                code_run_tool._docker_checked = False
                code_run_tool._docker_client = None

                # First check
                code_run_tool._check_docker_available()
                # Second check (should use cache)
                code_run_tool._check_docker_available()

                # from_env should only be called once
                assert mock_docker.from_env.call_count == 1
        finally:
            # Restore original
            if original_docker is None and hasattr(cr, 'docker'):
                delattr(cr, 'docker')
            elif original_docker is not None:
                cr.docker = original_docker

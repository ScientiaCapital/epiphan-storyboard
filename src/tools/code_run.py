"""Code execution tool for running Python and JavaScript in sandboxed environments."""

import asyncio
import logging
import sys
from typing import Any, Literal

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult

logger = logging.getLogger(__name__)

# Try to import Docker SDK
try:
    import docker
    from docker.errors import DockerException
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    DockerException = Exception  # Fallback for when docker is not installed
    logger.warning("Docker SDK not available - code execution will fall back to subprocess")


class CodeRunTool(BaseTool):
    """
    Tool for executing Python and JavaScript code in sandboxed environments.

    Uses Docker containers for isolation with resource limits when available.
    Falls back to subprocess execution if Docker is unavailable.

    Security features:
    - No network access in sandbox
    - Memory limits (128MB)
    - CPU limits (50% of one core)
    - Timeout enforcement (default 30s, max 60s)
    - Read-only root filesystem (Docker only)
    - Auto-cleanup after execution
    - No shell execution (uses execFile-style approach)
    """

    # Constants
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_TIMEOUT = 60  # seconds
    MEMORY_LIMIT = "128m"  # 128 MB
    CPU_PERIOD = 100000  # 100ms
    CPU_QUOTA = 50000  # 50ms of 100ms = 50% CPU

    # Docker images
    PYTHON_IMAGE = "python:3.11-slim"
    NODE_IMAGE = "node:20-slim"

    def __init__(self):
        """Initialize the code run tool."""
        self._docker_client = None
        self._docker_checked = False

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for code_run."""
        return ToolDefinition(
            name="code_run",
            description="Execute Python or JavaScript code in a sandboxed environment",
            category=ToolCategory.CODE,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to execute",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (python or javascript)",
                        "enum": ["python", "javascript"],
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": self.DEFAULT_TIMEOUT,
                        "minimum": 1,
                        "maximum": self.MAX_TIMEOUT,
                    },
                },
                "required": ["code", "language"],
            },
        )

    def _check_docker_available(self) -> bool:
        """
        Check if Docker is available and accessible.

        Returns:
            bool: True if Docker is available, False otherwise
        """
        if not DOCKER_AVAILABLE:
            return False

        if self._docker_checked:
            return self._docker_client is not None

        try:
            self._docker_client = docker.from_env()
            # Test Docker connectivity
            self._docker_client.ping()
            self._docker_checked = True
            logger.info("Docker is available for code execution")
            return True
        except (DockerException, Exception) as e:
            logger.warning(f"Docker not available: {e}")
            self._docker_client = None
            self._docker_checked = True
            return False

    async def _run_in_docker(
        self,
        code: str,
        language: Literal["python", "javascript"],
        timeout: int,
    ) -> dict[str, Any]:
        """
        Execute code in a Docker container.

        Args:
            code: Code to execute
            language: Programming language
            timeout: Timeout in seconds

        Returns:
            dict: Execution result with stdout, stderr, exit_code
        """
        if not self._docker_client:
            raise RuntimeError("Docker client not initialized")

        # Select image and command based on language
        # Using list format (not shell) to prevent injection
        if language == "python":
            image = self.PYTHON_IMAGE
            # Use 'python3' in Docker container (standard in python images)
            command = ["python3", "-c", code]
        else:  # javascript
            image = self.NODE_IMAGE
            command = ["node", "-e", code]

        try:
            # Pull image if not present (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._docker_client.images.pull(image)
            )

            # Run container with security restrictions
            container = await loop.run_in_executor(
                None,
                lambda: self._docker_client.containers.run(
                    image=image,
                    command=command,
                    remove=False,  # We'll remove manually after getting logs
                    detach=True,
                    network_mode="none",  # No network access
                    mem_limit=self.MEMORY_LIMIT,  # Memory limit
                    cpu_period=self.CPU_PERIOD,  # CPU period
                    cpu_quota=self.CPU_QUOTA,  # CPU quota (50% of one core)
                    read_only=True,  # Read-only root filesystem
                    tmpfs={"/tmp": "rw,noexec,nosuid,size=10m"},  # Writable /tmp
                )
            )

            # Wait for container to finish with timeout
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: container.wait(timeout=timeout)
                    ),
                    timeout=timeout + 1,  # Give extra second for cleanup
                )
                exit_code = result.get("StatusCode", -1)
            except asyncio.TimeoutError:
                # Kill container if it times out
                await loop.run_in_executor(None, container.kill)
                stdout = b""
                stderr = f"Execution timed out after {timeout} seconds".encode()
                exit_code = 124  # Standard timeout exit code
            else:
                # Get logs - Docker interleaves stdout and stderr
                # We'll get both in combined output
                combined_logs = await loop.run_in_executor(
                    None,
                    lambda: container.logs(stdout=True, stderr=True)
                )
                # For simplicity, put all output in stdout
                # (Docker doesn't separate them easily without demux)
                stdout = combined_logs
                stderr = b""

            # Remove container
            await loop.run_in_executor(None, lambda: container.remove(force=True))

            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": exit_code,
                "execution_method": "docker",
                "language": language,
            }

        except DockerException as e:
            logger.error(f"Docker execution failed: {e}")
            raise RuntimeError(f"Docker execution failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Docker execution: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")

    async def _run_in_subprocess(
        self,
        code: str,
        language: Literal["python", "javascript"],
        timeout: int,
    ) -> dict[str, Any]:
        """
        Execute code using subprocess (fallback when Docker unavailable).

        Args:
            code: Code to execute
            language: Programming language
            timeout: Timeout in seconds

        Returns:
            dict: Execution result with stdout, stderr, exit_code

        Note:
            This is less secure than Docker execution and should only be used
            as a fallback for development environments.
            Uses create_subprocess_exec (not shell) to prevent command injection.
        """
        # Select command based on language
        # Using array format prevents shell injection
        if language == "python":
            # Use sys.executable to get current Python interpreter
            # This ensures compatibility across systems (python vs python3)
            cmd_args = [sys.executable, "-c", code]
        else:  # javascript
            cmd_args = ["node", "-e", code]

        try:
            # Run subprocess with timeout
            # Using create_subprocess_exec (not shell=True) prevents injection
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
                exit_code = process.returncode
            except asyncio.TimeoutError:
                # Kill process if it times out
                process.kill()
                await process.wait()
                stdout = b""
                stderr = f"Execution timed out after {timeout} seconds".encode()
                exit_code = 124  # Standard timeout exit code

            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": exit_code,
                "execution_method": "subprocess",
                "language": language,
            }

        except FileNotFoundError:
            interpreter = "Python" if language == "python" else "Node.js"
            raise RuntimeError(f"{interpreter} interpreter not found in PATH")
        except Exception as e:
            logger.error(f"Subprocess execution failed: {e}")
            raise RuntimeError(f"Subprocess execution failed: {str(e)}")

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute code in a sandboxed environment.

        Args:
            arguments: Tool arguments containing code, language, timeout

        Returns:
            ToolResult with execution output or error
        """
        # Extract and validate arguments
        code = arguments.get("code")
        language = arguments.get("language")
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)

        # Validate required arguments
        if not code or not code.strip():
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Code parameter is required and cannot be empty",
                execution_time_ms=0,
            )

        if language not in ["python", "javascript"]:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Invalid language: {language}. Must be 'python' or 'javascript'",
                execution_time_ms=0,
            )

        # Validate timeout
        if not isinstance(timeout, int) or timeout < 1 or timeout > self.MAX_TIMEOUT:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Timeout must be an integer between 1 and {self.MAX_TIMEOUT}",
                execution_time_ms=0,
            )

        # Execute code
        try:
            # Check if Docker is available
            docker_available = self._check_docker_available()

            if docker_available:
                result_data = await self._run_in_docker(code, language, timeout)
            else:
                logger.warning("Using subprocess fallback for code execution (less secure)")
                result_data = await self._run_in_subprocess(code, language, timeout)

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=result_data,
                error=None,
                execution_time_ms=0,  # Will be set by _execute_with_timing
            )

        except RuntimeError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=0,
            )
        except Exception as e:
            logger.error(f"Unexpected error during code execution: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Unexpected error during code execution",
                execution_time_ms=0,
            )

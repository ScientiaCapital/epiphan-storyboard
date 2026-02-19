"""SQL query tool for executing queries against Supabase PostgreSQL database."""

import os
import re
from typing import Any

import asyncpg

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


class SqlQueryTool(BaseTool):
    """
    Tool for executing SQL queries against Supabase PostgreSQL database.

    Security features:
    - Blocks dangerous DDL/DCL operations (DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE)
    - Blocks DELETE/UPDATE without WHERE clause
    - Requires approval for all queries
    - Supports parameterized queries to prevent SQL injection
    - Limits result set size to prevent memory issues
    - Validates connection string from environment
    """

    # Constants for security and performance
    DEFAULT_MAX_ROWS = 100
    ABSOLUTE_MAX_ROWS = 1000

    # Dangerous SQL patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r"\bDROP\b",
        r"\bTRUNCATE\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
    ]

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for sql_query."""
        return ToolDefinition(
            name="sql_query",
            description="Execute SQL queries against the Supabase PostgreSQL database",
            category=ToolCategory.DATA,
            requires_approval=True,  # All SQL queries require approval for safety
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (supports $1, $2, ... for parameters)",
                    },
                    "params": {
                        "type": "array",
                        "description": "Query parameters for parameterized queries",
                        "items": {"type": ["string", "number", "boolean", "null"]},
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum rows to return",
                        "default": self.DEFAULT_MAX_ROWS,
                        "minimum": 1,
                        "maximum": self.ABSOLUTE_MAX_ROWS,
                    },
                },
                "required": ["query"],
            },
        )

    def _detect_dangerous_patterns(self, query: str) -> str | None:
        """
        Check for dangerous SQL patterns that should be blocked.

        Args:
            query: SQL query to check

        Returns:
            Error message if dangerous pattern detected, None otherwise
        """
        query_upper = query.upper()

        # Check for dangerous DDL/DCL operations
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, query_upper):
                operation = pattern.replace(r"\b", "").replace("\\", "")
                return f"{operation} operations are not allowed"

        return None

    def _validate_delete_update(self, query: str) -> str | None:
        """
        Validate DELETE and UPDATE statements require WHERE clause.

        Args:
            query: SQL query to validate

        Returns:
            Error message if invalid, None otherwise
        """
        query_upper = query.upper()

        # Check DELETE without WHERE
        if re.search(r"\bDELETE\s+FROM\b", query_upper):
            if not re.search(r"\bWHERE\b", query_upper):
                return "DELETE queries must include a WHERE clause"

        # Check UPDATE without WHERE
        if re.search(r"\bUPDATE\b", query_upper):
            if not re.search(r"\bWHERE\b", query_upper):
                return "UPDATE queries must include a WHERE clause"

        return None

    def _validate_query(self, query: str) -> str | None:
        """
        Validate SQL query for security issues.

        Args:
            query: SQL query to validate

        Returns:
            Error message if validation fails, None if valid
        """
        # Check for dangerous patterns
        error = self._detect_dangerous_patterns(query)
        if error:
            return error

        # Validate DELETE/UPDATE have WHERE clause
        error = self._validate_delete_update(query)
        if error:
            return error

        return None

    def _determine_query_type(self, query: str) -> str:
        """
        Determine the type of SQL query.

        Args:
            query: SQL query to analyze

        Returns:
            Query type (SELECT, INSERT, UPDATE, DELETE, or UNKNOWN)
        """
        query_upper = query.strip().upper()

        if query_upper.startswith("SELECT"):
            return "SELECT"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        else:
            return "UNKNOWN"

    async def _get_connection_string(self) -> str:
        """
        Get Supabase database connection string from environment.

        Returns:
            PostgreSQL connection string

        Raises:
            ValueError: If connection string not found in environment
        """
        conn_str = os.getenv("SUPABASE_DB_URL")
        if not conn_str:
            raise ValueError(
                "SUPABASE_DB_URL environment variable not set. "
                "Please configure database connection string."
            )
        return conn_str

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute SQL query against Supabase PostgreSQL database.

        Args:
            arguments: Tool arguments containing query, params, max_rows

        Returns:
            ToolResult with query results or error
        """
        # Extract arguments
        query = arguments.get("query", "").strip()
        params = arguments.get("params", [])
        max_rows = min(
            arguments.get("max_rows", self.DEFAULT_MAX_ROWS),
            self.ABSOLUTE_MAX_ROWS,
        )

        # Validate query is not empty
        if not query:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Query cannot be empty",
                execution_time_ms=0,
            )

        # Validate query for security issues
        validation_error = self._validate_query(query)
        if validation_error:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=validation_error,
                execution_time_ms=0,
            )

        # Get connection string
        try:
            conn_str = await self._get_connection_string()
        except ValueError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=0,
            )

        # Execute query
        conn = None
        try:
            # Connect to database
            conn = await asyncpg.connect(conn_str)

            # Determine query type
            query_type = self._determine_query_type(query)

            # Execute query based on type
            if query_type == "SELECT":
                # For SELECT, fetch rows with limit
                rows = await conn.fetch(query, *params, timeout=30.0)

                # Check if results were truncated
                truncated = len(rows) > max_rows
                rows = rows[:max_rows]

                # Extract column names and convert rows to dicts
                columns = list(rows[0].keys()) if rows else []
                row_dicts = [dict(row) for row in rows]

                result_data = {
                    "row_count": len(row_dicts),
                    "columns": columns,
                    "rows": row_dicts,
                    "truncated": truncated,
                    "query_type": query_type,
                }

            elif query_type in ("INSERT", "UPDATE", "DELETE"):
                # For DML operations, execute and get affected row count
                status = await conn.execute(query, *params, timeout=30.0)

                # Extract affected row count from status string
                # INSERT: "INSERT oid count" -> use last part
                # UPDATE: "UPDATE count" -> use last part
                # DELETE: "DELETE count" -> use last part
                affected_rows = 0
                if status:
                    parts = status.split()
                    if parts and parts[-1].isdigit():
                        affected_rows = int(parts[-1])

                result_data = {
                    "row_count": affected_rows,
                    "columns": [],
                    "rows": [],
                    "truncated": False,
                    "query_type": query_type,
                    "status": status,
                }

            else:
                # Unknown query type
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    result=None,
                    error=f"Unsupported query type: {query_type}",
                    execution_time_ms=0,
                )

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=result_data,
                error=None,
                execution_time_ms=0,  # Will be set by _execute_with_timing
            )

        except asyncpg.PostgresError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Database error: {str(e)}",
                execution_time_ms=0,
            )
        except asyncpg.InterfaceError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Database connection error: {str(e)}",
                execution_time_ms=0,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Unexpected error: {str(e)}",
                execution_time_ms=0,
            )
        finally:
            # Ensure connection is closed
            if conn is not None:
                await conn.close()

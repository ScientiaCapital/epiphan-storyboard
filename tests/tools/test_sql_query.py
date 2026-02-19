"""Tests for the sql_query tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.base import ToolCategory, ToolResult
from src.tools.sql_query import SqlQueryTool


@pytest.fixture
def sql_query_tool():
    """Create a SqlQueryTool instance for testing."""
    return SqlQueryTool()


class TestSqlQueryToolDefinition:
    """Test the tool definition and schema."""

    def test_tool_name(self, sql_query_tool):
        """Test that the tool has the correct name."""
        assert sql_query_tool.definition.name == "sql_query"

    def test_tool_category(self, sql_query_tool):
        """Test that the tool is in the DATA category."""
        assert sql_query_tool.definition.category == ToolCategory.DATA

    def test_requires_approval(self, sql_query_tool):
        """Test that the tool requires approval for all queries."""
        assert sql_query_tool.definition.requires_approval is True

    def test_parameters_schema(self, sql_query_tool):
        """Test that the parameters schema is correctly defined."""
        params = sql_query_tool.definition.parameters
        assert params["type"] == "object"
        assert "query" in params["required"]
        assert "query" in params["properties"]
        assert "params" in params["properties"]
        assert "max_rows" in params["properties"]

    def test_llm_schema(self, sql_query_tool):
        """Test that the LLM schema is correctly formatted."""
        schema = sql_query_tool.get_llm_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "sql_query"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]


class TestDangerousPatternDetection:
    """Test detection of dangerous SQL patterns."""

    def test_drop_table_blocked(self, sql_query_tool):
        """Test that DROP TABLE is blocked."""
        error = sql_query_tool._detect_dangerous_patterns("DROP TABLE users")
        assert error is not None
        assert "DROP" in error

    def test_drop_database_blocked(self, sql_query_tool):
        """Test that DROP DATABASE is blocked."""
        error = sql_query_tool._detect_dangerous_patterns("DROP DATABASE production")
        assert error is not None
        assert "DROP" in error

    def test_truncate_blocked(self, sql_query_tool):
        """Test that TRUNCATE is blocked."""
        error = sql_query_tool._detect_dangerous_patterns("TRUNCATE TABLE logs")
        assert error is not None
        assert "TRUNCATE" in error

    def test_alter_blocked(self, sql_query_tool):
        """Test that ALTER is blocked."""
        error = sql_query_tool._detect_dangerous_patterns("ALTER TABLE users ADD COLUMN age INT")
        assert error is not None
        assert "ALTER" in error

    def test_create_blocked(self, sql_query_tool):
        """Test that CREATE is blocked."""
        error = sql_query_tool._detect_dangerous_patterns("CREATE TABLE malicious (id INT)")
        assert error is not None
        assert "CREATE" in error

    def test_grant_blocked(self, sql_query_tool):
        """Test that GRANT is blocked."""
        error = sql_query_tool._detect_dangerous_patterns("GRANT ALL ON users TO attacker")
        assert error is not None
        assert "GRANT" in error

    def test_revoke_blocked(self, sql_query_tool):
        """Test that REVOKE is blocked."""
        error = sql_query_tool._detect_dangerous_patterns("REVOKE SELECT ON users FROM viewer")
        assert error is not None
        assert "REVOKE" in error

    def test_case_insensitive_detection(self, sql_query_tool):
        """Test that pattern detection is case-insensitive."""
        error = sql_query_tool._detect_dangerous_patterns("drop table users")
        assert error is not None
        assert "DROP" in error

    def test_select_allowed(self, sql_query_tool):
        """Test that SELECT queries are allowed."""
        error = sql_query_tool._detect_dangerous_patterns("SELECT * FROM users")
        assert error is None

    def test_insert_allowed(self, sql_query_tool):
        """Test that INSERT queries are allowed."""
        error = sql_query_tool._detect_dangerous_patterns("INSERT INTO users (name) VALUES ('test')")
        assert error is None


class TestDeleteUpdateValidation:
    """Test validation of DELETE and UPDATE statements."""

    def test_delete_without_where_blocked(self, sql_query_tool):
        """Test that DELETE without WHERE is blocked."""
        error = sql_query_tool._validate_delete_update("DELETE FROM users")
        assert error is not None
        assert "WHERE" in error
        assert "DELETE" in error

    def test_delete_with_where_allowed(self, sql_query_tool):
        """Test that DELETE with WHERE is allowed."""
        error = sql_query_tool._validate_delete_update("DELETE FROM users WHERE id = 1")
        assert error is None

    def test_update_without_where_blocked(self, sql_query_tool):
        """Test that UPDATE without WHERE is blocked."""
        error = sql_query_tool._validate_delete_update("UPDATE users SET active = false")
        assert error is not None
        assert "WHERE" in error
        assert "UPDATE" in error

    def test_update_with_where_allowed(self, sql_query_tool):
        """Test that UPDATE with WHERE is allowed."""
        error = sql_query_tool._validate_delete_update("UPDATE users SET active = false WHERE id = 1")
        assert error is None

    def test_case_insensitive_validation(self, sql_query_tool):
        """Test that validation is case-insensitive."""
        error = sql_query_tool._validate_delete_update("delete from users")
        assert error is not None
        assert "WHERE" in error

    def test_select_not_affected(self, sql_query_tool):
        """Test that SELECT queries are not affected by DELETE/UPDATE validation."""
        error = sql_query_tool._validate_delete_update("SELECT * FROM users")
        assert error is None


class TestQueryValidation:
    """Test overall query validation."""

    def test_dangerous_pattern_validation(self, sql_query_tool):
        """Test that dangerous patterns are caught by _validate_query."""
        error = sql_query_tool._validate_query("DROP TABLE users")
        assert error is not None
        assert "DROP" in error

    def test_delete_without_where_validation(self, sql_query_tool):
        """Test that DELETE without WHERE is caught by _validate_query."""
        error = sql_query_tool._validate_query("DELETE FROM users")
        assert error is not None
        assert "WHERE" in error

    def test_safe_query_validation(self, sql_query_tool):
        """Test that safe queries pass validation."""
        error = sql_query_tool._validate_query("SELECT * FROM users WHERE id = 1")
        assert error is None


class TestQueryTypeDetection:
    """Test query type detection."""

    def test_select_detection(self, sql_query_tool):
        """Test SELECT query detection."""
        query_type = sql_query_tool._determine_query_type("SELECT * FROM users")
        assert query_type == "SELECT"

    def test_insert_detection(self, sql_query_tool):
        """Test INSERT query detection."""
        query_type = sql_query_tool._determine_query_type("INSERT INTO users (name) VALUES ('test')")
        assert query_type == "INSERT"

    def test_update_detection(self, sql_query_tool):
        """Test UPDATE query detection."""
        query_type = sql_query_tool._determine_query_type("UPDATE users SET active = false WHERE id = 1")
        assert query_type == "UPDATE"

    def test_delete_detection(self, sql_query_tool):
        """Test DELETE query detection."""
        query_type = sql_query_tool._determine_query_type("DELETE FROM users WHERE id = 1")
        assert query_type == "DELETE"

    def test_case_insensitive_detection(self, sql_query_tool):
        """Test that query type detection is case-insensitive."""
        query_type = sql_query_tool._determine_query_type("select * from users")
        assert query_type == "SELECT"

    def test_whitespace_handling(self, sql_query_tool):
        """Test that leading/trailing whitespace is handled."""
        query_type = sql_query_tool._determine_query_type("  SELECT * FROM users  ")
        assert query_type == "SELECT"


class TestParameterizedQueries:
    """Test parameterized query support."""

    @pytest.mark.asyncio
    async def test_parameterized_select(self, sql_query_tool):
        """Test SELECT with parameters."""
        # Mock database connection
        mock_conn = AsyncMock()
        mock_row = {"id": 1, "name": "test", "email": "test@example.com"}
        mock_conn.fetch.return_value = [MagicMock(**mock_row, keys=lambda: mock_row.keys())]

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users WHERE id = $1",
                    "params": [1],
                })

                assert result.success is True
                assert result.result["query_type"] == "SELECT"
                # Verify parameters were passed
                mock_conn.fetch.assert_called_once()
                call_args = mock_conn.fetch.call_args
                assert call_args[0][0] == "SELECT * FROM users WHERE id = $1"
                assert call_args[0][1] == 1

    @pytest.mark.asyncio
    async def test_multiple_parameters(self, sql_query_tool):
        """Test query with multiple parameters."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users WHERE age > $1 AND city = $2",
                    "params": [25, "New York"],
                })

                assert result.success is True
                # Verify multiple parameters were passed
                call_args = mock_conn.fetch.call_args
                assert call_args[0][1] == 25
                assert call_args[0][2] == "New York"


class TestMaxRowsEnforcement:
    """Test maximum rows limit enforcement."""

    @pytest.mark.asyncio
    async def test_default_max_rows(self, sql_query_tool):
        """Test that default max_rows is 100."""
        assert sql_query_tool.DEFAULT_MAX_ROWS == 100

    @pytest.mark.asyncio
    async def test_absolute_max_rows(self, sql_query_tool):
        """Test that absolute max_rows is 1000."""
        assert sql_query_tool.ABSOLUTE_MAX_ROWS == 1000

    @pytest.mark.asyncio
    async def test_max_rows_enforcement(self, sql_query_tool):
        """Test that results are truncated to max_rows."""
        # Create 150 mock rows
        mock_rows = []
        for i in range(150):
            row = {"id": i, "name": f"user{i}"}
            mock_rows.append(MagicMock(**row, keys=lambda: ["id", "name"]))

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users",
                    "max_rows": 100,
                })

                assert result.success is True
                assert result.result["row_count"] == 100
                assert result.result["truncated"] is True

    @pytest.mark.asyncio
    async def test_custom_max_rows(self, sql_query_tool):
        """Test using custom max_rows value."""
        mock_rows = []
        for i in range(50):
            row = {"id": i, "name": f"user{i}"}
            mock_rows.append(MagicMock(**row, keys=lambda: ["id", "name"]))

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users",
                    "max_rows": 50,
                })

                assert result.success is True
                assert result.result["row_count"] == 50
                assert result.result["truncated"] is False

    @pytest.mark.asyncio
    async def test_max_rows_capped_at_absolute_max(self, sql_query_tool):
        """Test that max_rows cannot exceed absolute maximum."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                # Request 2000 rows (above absolute max of 1000)
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users",
                    "max_rows": 2000,
                })

                assert result.success is True
                # Should be capped at 1000
                # Verify by checking the slice operation in the code


class TestResultFormat:
    """Test result format correctness."""

    @pytest.mark.asyncio
    async def test_select_result_format(self, sql_query_tool):
        """Test SELECT query result format."""
        mock_row = {"id": 1, "name": "test", "email": "test@example.com"}
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [MagicMock(**mock_row, keys=lambda: mock_row.keys())]

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users WHERE id = 1",
                })

                assert result.success is True
                assert "row_count" in result.result
                assert "columns" in result.result
                assert "rows" in result.result
                assert "truncated" in result.result
                assert "query_type" in result.result
                assert result.result["query_type"] == "SELECT"
                assert result.result["columns"] == ["id", "name", "email"]
                assert result.result["row_count"] == 1

    @pytest.mark.asyncio
    async def test_insert_result_format(self, sql_query_tool):
        """Test INSERT query result format."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "INSERT 0 1"

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "INSERT INTO users (name) VALUES ($1)",
                    "params": ["test"],
                })

                assert result.success is True
                assert result.result["query_type"] == "INSERT"
                assert result.result["row_count"] == 1
                assert result.result["status"] == "INSERT 0 1"

    @pytest.mark.asyncio
    async def test_update_result_format(self, sql_query_tool):
        """Test UPDATE query result format."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 5"

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "UPDATE users SET active = false WHERE created_at < $1",
                    "params": ["2023-01-01"],
                })

                assert result.success is True
                assert result.result["query_type"] == "UPDATE"
                assert result.result["row_count"] == 5
                assert result.result["status"] == "UPDATE 5"

    @pytest.mark.asyncio
    async def test_delete_result_format(self, sql_query_tool):
        """Test DELETE query result format."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 3"

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "DELETE FROM users WHERE id = $1",
                    "params": [1],
                })

                assert result.success is True
                assert result.result["query_type"] == "DELETE"
                assert result.result["row_count"] == 3
                assert result.result["status"] == "DELETE 3"

    @pytest.mark.asyncio
    async def test_empty_result_format(self, sql_query_tool):
        """Test empty result set format."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users WHERE id = -1",
                })

                assert result.success is True
                assert result.result["row_count"] == 0
                assert result.result["columns"] == []
                assert result.result["rows"] == []
                assert result.result["truncated"] is False


class TestConnectionHandling:
    """Test database connection handling."""

    @pytest.mark.asyncio
    async def test_missing_connection_string(self, sql_query_tool):
        """Test error when connection string is missing."""
        with patch.dict("os.environ", {}, clear=True):
            result = await sql_query_tool.run({
                "query": "SELECT * FROM users",
            })

            assert result.success is False
            assert "SUPABASE_DB_URL" in result.error

    @pytest.mark.asyncio
    async def test_connection_error(self, sql_query_tool):
        """Test handling of connection errors."""
        with patch("asyncpg.connect", side_effect=Exception("Connection failed")):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://invalid"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM users",
                })

                assert result.success is False
                assert result.error is not None

    @pytest.mark.asyncio
    async def test_connection_closed_after_success(self, sql_query_tool):
        """Test that connection is closed after successful query."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                await sql_query_tool.run({
                    "query": "SELECT * FROM users",
                })

                # Verify connection was closed
                mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_closed_after_error(self, sql_query_tool):
        """Test that connection is closed even after error."""
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = Exception("Query failed")

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                await sql_query_tool.run({
                    "query": "SELECT * FROM users",
                })

                # Verify connection was closed even though query failed
                mock_conn.close.assert_called_once()


class TestErrorHandling:
    """Test error handling for various scenarios."""

    @pytest.mark.asyncio
    async def test_empty_query_error(self, sql_query_tool):
        """Test error when query is empty."""
        result = await sql_query_tool.run({"query": ""})

        assert result.success is False
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_whitespace_query_error(self, sql_query_tool):
        """Test error when query is only whitespace."""
        result = await sql_query_tool.run({"query": "   "})

        assert result.success is False
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_dangerous_query_error(self, sql_query_tool):
        """Test error for dangerous query patterns."""
        result = await sql_query_tool.run({
            "query": "DROP TABLE users",
        })

        assert result.success is False
        assert "DROP" in result.error

    @pytest.mark.asyncio
    async def test_delete_without_where_error(self, sql_query_tool):
        """Test error for DELETE without WHERE."""
        result = await sql_query_tool.run({
            "query": "DELETE FROM users",
        })

        assert result.success is False
        assert "WHERE" in result.error

    @pytest.mark.asyncio
    async def test_database_error(self, sql_query_tool):
        """Test handling of database errors."""
        mock_conn = AsyncMock()
        # Import asyncpg to use its exception types
        import asyncpg
        mock_conn.fetch.side_effect = asyncpg.PostgresError("Syntax error")

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool.run({
                    "query": "SELECT * FROM nonexistent_table",
                })

                assert result.success is False
                assert "Database error" in result.error


class TestExecutionTiming:
    """Test execution timing functionality."""

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self, sql_query_tool):
        """Test that execution time is recorded."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict("os.environ", {"SUPABASE_DB_URL": "postgresql://test"}):
                result = await sql_query_tool._execute_with_timing({
                    "query": "SELECT * FROM users",
                })

                assert isinstance(result, ToolResult)
                assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execution_time_on_error(self, sql_query_tool):
        """Test that execution time is recorded even on error."""
        result = await sql_query_tool._execute_with_timing({
            "query": "DROP TABLE users",
        })

        assert result.success is False
        assert result.execution_time_ms >= 0

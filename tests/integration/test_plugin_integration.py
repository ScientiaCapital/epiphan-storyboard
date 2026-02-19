"""Integration tests for 3-way plugin system.

Tests integration between:
- conductor-ai (SDK + observability)
- dealer-scraper-mvp (scraper plugin tools)
- sales-agent (sales plugin tools)
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project paths for cross-project imports
CONDUCTOR_ROOT = Path(__file__).parent.parent.parent
DEALER_SCRAPER_ROOT = CONDUCTOR_ROOT.parent / "dealer-scraper-mvp"
SALES_AGENT_ROOT = CONDUCTOR_ROOT.parent / "sales-agent"

sys.path.insert(0, str(CONDUCTOR_ROOT))
sys.path.insert(0, str(DEALER_SCRAPER_ROOT))
sys.path.insert(0, str(SALES_AGENT_ROOT))


class TestAuditLayerIntegration:
    """Test audit layer captures tool executions."""

    def test_audit_logger_creation(self):
        """Can create audit logger."""
        from src.observability.audit import AuditLogger

        logger = AuditLogger(org_id="test-org")
        assert logger.org_id == "test-org"

    def test_audit_tool_call(self):
        """Audit logger captures tool calls."""
        from src.observability.audit import AuditLogger

        # source_project is set in constructor
        logger = AuditLogger(org_id="test-org", source_project="dealer-scraper-mvp")
        record = logger.log_tool_call(
            tool_name="dealer_locator",
            input_params={"oem": "generac", "zip_code": "53202"},
            success=True,
            output_summary="Found 5 dealers",
        )

        assert record.tool_name == "dealer_locator"
        assert record.source_project == "dealer-scraper-mvp"
        assert record.success is True

    @pytest.mark.asyncio
    async def test_audit_logged_decorator(self):
        """@audit_logged decorator captures function calls."""
        from src.observability.audit import AuditLogger, audit_logged

        logger = AuditLogger(org_id="test-org")

        @audit_logged(logger, "test_tool")
        async def sample_function(x, y):
            return x + y

        result = await sample_function(2, 3)
        assert result == 5

        logs = logger.get_recent_logs()
        assert len(logs) == 1
        assert logs[0].tool_name == "test_tool"
        assert logs[0].success is True


class TestDealerScraperPluginIntegration:
    """Test dealer-scraper-mvp plugin integration."""

    @pytest.fixture
    def mock_scraper_factory(self):
        """Mock ScraperFactory to avoid actual web scraping."""
        with patch.dict(sys.modules, {'scrapers.scraper_factory': MagicMock()}):
            mock_factory = MagicMock()
            mock_scraper = MagicMock()
            mock_scraper.scrape_zip_code.return_value = [
                {"name": "ABC Solar", "phone": "555-0123"},
                {"name": "XYZ Generators", "phone": "555-0456"},
            ]
            mock_factory.create.return_value = mock_scraper
            mock_factory.list_available_oems.return_value = ["generac", "tesla"]

            sys.modules['scrapers'] = MagicMock()
            sys.modules['scrapers.scraper_factory'] = mock_factory
            sys.modules['scrapers.scraper_factory'].ScraperFactory = mock_factory

            yield mock_factory

    @pytest.fixture
    def mock_enrichment(self):
        """Mock enrichment modules."""
        mock_apollo = MagicMock()
        mock_apollo.return_value.enrich_company.return_value = {
            "employee_count": 50,
            "revenue_range": "$5M-$10M",
        }

        with patch.dict(sys.modules, {
            'enrichment': MagicMock(),
            'enrichment.ApolloEnricher': mock_apollo,
            'enrichment.ClayEnricher': MagicMock(),
            'enrichment.HunterEnricher': MagicMock(),
        }):
            yield

    def test_dealer_locator_tool_exists(self):
        """DealerLocatorTool can be imported."""
        import importlib.util
        dealer_plugins_path = DEALER_SCRAPER_ROOT / "plugins" / "scraper_tools"

        # Import base first
        spec = importlib.util.spec_from_file_location(
            "scraper_tools.base",
            dealer_plugins_path / "base.py"
        )
        base_module = importlib.util.module_from_spec(spec)
        sys.modules["plugins.scraper_tools.base"] = base_module
        spec.loader.exec_module(base_module)

        # Import dealer locator
        spec = importlib.util.spec_from_file_location(
            "scraper_tools.dealer_locator",
            dealer_plugins_path / "dealer_locator.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.DealerLocatorTool()
        assert tool.definition.name == "dealer_locator"

    def test_contractor_enrich_tool_exists(self):
        """ContractorEnrichTool can be imported."""
        import importlib.util
        dealer_plugins_path = DEALER_SCRAPER_ROOT / "plugins" / "scraper_tools"

        # Import base first (may already be loaded)
        if "plugins.scraper_tools.base" not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                "scraper_tools.base",
                dealer_plugins_path / "base.py"
            )
            base_module = importlib.util.module_from_spec(spec)
            sys.modules["plugins.scraper_tools.base"] = base_module
            spec.loader.exec_module(base_module)

        # Mock enrichment module since we don't have it
        sys.modules["enrichment"] = MagicMock()

        spec = importlib.util.spec_from_file_location(
            "scraper_tools.contractor_enrich",
            dealer_plugins_path / "contractor_enrich.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.ContractorEnrichTool()
        assert tool.definition.name == "contractor_enrich"

    def test_license_validate_tool_exists(self):
        """LicenseValidateTool can be imported."""
        import importlib.util
        dealer_plugins_path = DEALER_SCRAPER_ROOT / "plugins" / "scraper_tools"

        # Import base first (may already be loaded)
        if "plugins.scraper_tools.base" not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                "scraper_tools.base",
                dealer_plugins_path / "base.py"
            )
            base_module = importlib.util.module_from_spec(spec)
            sys.modules["plugins.scraper_tools.base"] = base_module
            spec.loader.exec_module(base_module)

        spec = importlib.util.spec_from_file_location(
            "scraper_tools.license_validate",
            dealer_plugins_path / "license_validate.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.LicenseValidateTool()
        assert tool.definition.name == "license_validate"

    def test_plugin_base_has_required_classes(self):
        """Plugin base module has all required classes."""
        import importlib.util
        dealer_plugins_path = DEALER_SCRAPER_ROOT / "plugins" / "scraper_tools"

        spec = importlib.util.spec_from_file_location(
            "scraper_tools.base",
            dealer_plugins_path / "base.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "BaseTool")
        assert hasattr(module, "ToolDefinition")
        assert hasattr(module, "ToolResult")
        assert hasattr(module, "ToolCategory")


class TestSalesAgentPluginIntegration:
    """Test sales-agent plugin integration."""

    def test_outreach_tool_exists(self):
        """OutreachTool can be imported from sales-agent."""
        # Import from sales-agent plugins
        sales_plugins_path = SALES_AGENT_ROOT / "plugins"
        if str(sales_plugins_path.parent) not in sys.path:
            sys.path.insert(0, str(sales_plugins_path.parent))

        # Use importlib for clean import
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sales_tools.outreach",
            sales_plugins_path / "sales_tools" / "outreach.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.OutreachTool()
        assert tool.definition.name == "outreach_send"

    def test_qualify_tool_exists(self):
        """QualifyTool can be imported from sales-agent."""
        import importlib.util
        sales_plugins_path = SALES_AGENT_ROOT / "plugins"

        spec = importlib.util.spec_from_file_location(
            "sales_tools.qualify",
            sales_plugins_path / "sales_tools" / "qualify.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.QualifyTool()
        assert tool.definition.name == "lead_qualify"

    def test_crm_sync_tool_exists(self):
        """CRMSyncTool can be imported from sales-agent."""
        import importlib.util
        sales_plugins_path = SALES_AGENT_ROOT / "plugins"

        spec = importlib.util.spec_from_file_location(
            "sales_tools.crm_sync",
            sales_plugins_path / "sales_tools" / "crm_sync.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.CRMSyncTool()
        assert tool.definition.name == "crm_sync"


class TestCrossProjectDataFlow:
    """Test data flows correctly between projects."""

    @pytest.mark.asyncio
    async def test_dealer_to_qualify_flow(self):
        """Data from dealer scraper can flow to qualification."""
        # Simulate dealer locator result
        dealer_result = {
            "name": "ABC Solar Co",
            "phone": "555-0123",
            "address": "123 Main St",
        }

        # Import qualify tool
        import importlib.util
        sales_plugins_path = SALES_AGENT_ROOT / "plugins"

        spec = importlib.util.spec_from_file_location(
            "sales_tools.qualify",
            sales_plugins_path / "sales_tools" / "qualify.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.QualifyTool()

        # Run qualification with enrichment data from dealer
        result = await tool.run({
            "lead_id": "lead-from-dealer",
            "enrichment_data": {
                "employee_count": 75,
                "revenue_range": "$5M-$10M",
            },
        })

        assert result.success is True
        assert result.result["score"] >= 70  # Should qualify

    @pytest.mark.asyncio
    async def test_audit_captures_cross_project_calls(self):
        """Audit layer logs tool calls from both projects."""
        from src.observability.audit import AuditLogger

        # Create loggers for each project
        dealer_logger = AuditLogger(org_id="integration-test", source_project="dealer-scraper-mvp")
        sales_logger = AuditLogger(org_id="integration-test", source_project="sales-agent")

        # Log dealer scraper tool call
        dealer_record = dealer_logger.log_tool_call(
            tool_name="dealer_locator",
            input_params={"oem": "generac", "zip_code": "53202"},
            success=True,
        )

        # Log sales agent tool calls
        qualify_record = sales_logger.log_tool_call(
            tool_name="lead_qualify",
            input_params={"lead_id": "lead-123"},
            success=True,
        )

        crm_record = sales_logger.log_tool_call(
            tool_name="crm_sync",
            input_params={"lead_id": "lead-123", "crm": "close"},
            success=True,
        )

        # Verify source projects
        assert dealer_record.source_project == "dealer-scraper-mvp"
        assert qualify_record.source_project == "sales-agent"
        assert crm_record.source_project == "sales-agent"

        # Verify tool names
        assert dealer_record.tool_name == "dealer_locator"
        assert qualify_record.tool_name == "lead_qualify"
        assert crm_record.tool_name == "crm_sync"

        # Verify logs can be retrieved per project
        assert len(dealer_logger.get_recent_logs()) == 1
        assert len(sales_logger.get_recent_logs()) == 2


class TestPluginToolCategoryCompatibility:
    """Test that tools have compatible categories."""

    def test_tool_categories_defined(self):
        """All plugins define tool categories."""
        import importlib.util

        # Dealer scraper tools
        dealer_plugins_path = DEALER_SCRAPER_ROOT / "plugins" / "scraper_tools"
        spec = importlib.util.spec_from_file_location(
            "scraper_tools.base_cat",
            dealer_plugins_path / "base.py"
        )
        dealer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dealer_module)

        ScraperCategory = dealer_module.ToolCategory
        assert hasattr(ScraperCategory, "WEB")
        assert hasattr(ScraperCategory, "DATA")

        # Sales agent tools
        sales_plugins_path = SALES_AGENT_ROOT / "plugins"

        spec = importlib.util.spec_from_file_location(
            "sales_tools.base_cat",
            sales_plugins_path / "sales_tools" / "base.py"
        )
        sales_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sales_module)

        SalesCategory = sales_module.ToolCategory
        assert hasattr(SalesCategory, "SALES")
        assert hasattr(SalesCategory, "DATA")

    def test_tool_result_compatible_structure(self):
        """ToolResult structures are compatible across plugins."""
        import importlib.util
        dealer_plugins_path = DEALER_SCRAPER_ROOT / "plugins" / "scraper_tools"

        spec = importlib.util.spec_from_file_location(
            "scraper_tools.base_result",
            dealer_plugins_path / "base.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        ScraperResult = module.ToolResult

        # Create a scraper result
        scraper_result = ScraperResult(
            tool_name="test",
            success=True,
            result={"data": "test"},
            execution_time_ms=100,
        )

        assert hasattr(scraper_result, "tool_name")
        assert hasattr(scraper_result, "success")
        assert hasattr(scraper_result, "result")
        assert hasattr(scraper_result, "execution_time_ms")
        assert hasattr(scraper_result, "error")

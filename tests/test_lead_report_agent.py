"""Tests for LeadReportAgent real flow vs demo."""
import unittest
from unittest.mock import patch, MagicMock


class TestLeadReportAgent(unittest.TestCase):
    def _make_agent(self):
        from core.agents.lead_report_agent import LeadReportAgent
        agent = LeadReportAgent.__new__(LeadReportAgent)
        agent.memory = MagicMock()
        return agent

    def test_run_demo_uses_sample_leads(self):
        agent = self._make_agent()
        with patch.object(agent.__class__, 'generate_report', return_value="ok") as mock:
            agent.run(["demo"])
            args = mock.call_args[0][0]
            self.assertIsInstance(args, list)
            self.assertGreater(len(args), 0)

    def test_run_empty_uses_sample_leads(self):
        agent = self._make_agent()
        with patch.object(agent.__class__, 'generate_report', return_value="ok") as mock:
            agent.run([])
            mock.assert_called_once()

    def test_run_real_leads_json(self):
        import json
        agent = self._make_agent()
        leads = [{"empresa": "XYZ", "pais": "BR", "setor": "tech"}]
        with patch.object(agent.__class__, 'generate_report', return_value="ok") as mock:
            agent.run([json.dumps(leads)])
            mock.assert_called_once_with(leads)

    def test_run_invalid_json_returns_error(self):
        agent = self._make_agent()
        result = agent.run(["not-json"])
        self.assertIn("Erro", result)

    def test_sample_leads_not_used_in_real_path(self):
        import json
        from core.agents.lead_report_agent import DEMO_LEADS
        agent = self._make_agent()
        real_leads = [{"empresa": "Real Corp", "pais": "US"}]
        with patch.object(agent.__class__, 'generate_report', return_value="ok") as mock:
            agent.run([json.dumps(real_leads)])
            called_with = mock.call_args[0][0]
            self.assertNotEqual(called_with, DEMO_LEADS)

    def test_run_production_passes_leads_directly(self):
        """run_production() should call generate_report with the exact leads list."""
        agent = self._make_agent()
        leads = [{"empresa": "Prod Corp", "pais": "US", "setor": "finance"}]
        with patch.object(agent.__class__, 'generate_report', return_value="prod-report") as mock:
            result = agent.run_production(leads)
            mock.assert_called_once_with(leads)
            self.assertEqual(result, "prod-report")

    def test_cli_style_json_string_in_run(self):
        """CLI passes run([json_string]); verify it reaches generate_report correctly."""
        import json
        agent = self._make_agent()
        leads = [{"empresa": "CLI Corp", "pais": "BR"}]
        json_str = json.dumps(leads)
        with patch.object(agent.__class__, 'generate_report', return_value="cli-report") as mock:
            result = agent.run([json_str])
            mock.assert_called_once_with(leads)
            self.assertEqual(result, "cli-report")


if __name__ == "__main__":
    unittest.main()

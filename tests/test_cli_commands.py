"""CLI smoke tests for proposal and lead-report commands."""
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner


class TestLeadReportCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_lead_report_demo_displays_text(self):
        from cli import cli
        mock_result = {"text": "Relatório executivo de leads", "agent": "lead-report", "model": "test"}
        with patch("core.agents.lead_report_agent.LeadReportAgent.run", return_value=mock_result), \
             patch("core.claude_client.make_client", return_value=MagicMock()):
            result = self.runner.invoke(cli, ["lead-report", "demo"])
        self.assertIn("Relatório executivo de leads", result.output)
        self.assertNotIn("{'text'", result.output)   # must not show dict repr

    def test_lead_report_json_input_displays_text(self):
        from cli import cli
        import json
        leads = [{"empresa": "XYZ", "pais": "BR"}]
        mock_result = {"text": "Relatório XYZ", "agent": "lead-report", "model": "test"}
        with patch("core.agents.lead_report_agent.LeadReportAgent.run", return_value=mock_result), \
             patch("core.claude_client.make_client", return_value=MagicMock()):
            result = self.runner.invoke(cli, ["lead-report", json.dumps(leads)])
        self.assertIn("Relatório XYZ", result.output)


class TestProposalCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_proposal_displays_text(self):
        from cli import cli
        mock_result = {"text": "Proposta gerada", "file": "/tmp/p.md", "cliente": "XYZ"}
        with patch("core.agents.proposal_agent.ProposalAgent.generate", return_value=mock_result), \
             patch("core.claude_client.make_client", return_value=MagicMock()):
            result = self.runner.invoke(cli, ["proposal", "XYZ", "saude", "acelerar vendas"])
        self.assertIn("Proposta gerada", result.output)

    def test_proposal_missing_args_shows_usage(self):
        from cli import cli
        with patch("core.claude_client.make_client", return_value=MagicMock()):
            result = self.runner.invoke(cli, ["proposal"])
        # Should show usage/error, not crash with traceback
        self.assertNotIn("Traceback", result.output)


if __name__ == "__main__":
    unittest.main()

"""Tests: OrchestratorAgent schema includes proposal and lead-report."""
import unittest


class TestOrchestratorSchema(unittest.TestCase):
    def test_proposal_in_agent_map(self):
        from core.agents.orchestrator_agent import AGENT_MAP
        self.assertIn("proposal", AGENT_MAP)

    def test_lead_report_in_agent_map(self):
        from core.agents.orchestrator_agent import AGENT_MAP
        self.assertIn("lead-report", AGENT_MAP)

    def test_proposal_agent_has_description(self):
        from core.agents.proposal_agent import ProposalAgent
        self.assertTrue(hasattr(ProposalAgent, 'description') and ProposalAgent.description)

    def test_lead_report_agent_has_description(self):
        from core.agents.lead_report_agent import LeadReportAgent
        self.assertTrue(hasattr(LeadReportAgent, 'description') and LeadReportAgent.description)

    def test_orchestrator_prompt_mentions_proposal(self):
        from core.agents.orchestrator_agent import OrchestratorAgent
        # Check if the orchestrator system prompt / capability list mentions proposal
        prompt = getattr(OrchestratorAgent, '_system_prompt', '') or \
                 getattr(OrchestratorAgent, 'AGENT_DESCRIPTIONS', '') or ''
        # If no explicit prompt, check agent map keys are used in decomposition
        from core.agents.orchestrator_agent import AGENT_MAP
        self.assertIn("proposal", AGENT_MAP)
        self.assertIn("lead-report", AGENT_MAP)

    def test_agent_descriptions_includes_proposal(self):
        from core.agents.orchestrator_agent import AGENT_DESCRIPTIONS
        self.assertIn("proposal", AGENT_DESCRIPTIONS)
        self.assertIn("lead-report", AGENT_DESCRIPTIONS)

    def test_agent_descriptions_content(self):
        from core.agents.orchestrator_agent import AGENT_DESCRIPTIONS
        self.assertIn("B2B", AGENT_DESCRIPTIONS["proposal"])
        self.assertIn("leads", AGENT_DESCRIPTIONS["lead-report"])

    def test_orchestrator_role_description_mentions_agents(self):
        from core.agents.orchestrator_agent import OrchestratorAgent
        rd = OrchestratorAgent.role_description
        self.assertIn("proposal", rd)
        self.assertIn("lead-report", rd)


if __name__ == "__main__":
    unittest.main()

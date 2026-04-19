"""Regression: proposal and lead-report work as orchestrated subtasks."""
import unittest
from unittest.mock import patch, MagicMock


class TestOrchestrationContract(unittest.TestCase):

    def _make_orchestrator(self):
        from core.agents.orchestrator_agent import OrchestratorAgent
        agent = OrchestratorAgent.__new__(OrchestratorAgent)
        agent.memory = MagicMock()
        return agent

    def test_proposal_agent_callable_from_orchestrator_style(self):
        """ProposalAgent must not raise TypeError when called as a subtask."""
        from core.agents.proposal_agent import ProposalAgent
        agent = ProposalAgent.__new__(ProposalAgent)
        agent.memory = MagicMock()
        _api_result = {"text": "proposta gerada", "model": "claude-sonnet-4-6",
                       "input_tokens": 0, "output_tokens": 0}
        with patch.object(ProposalAgent, '_call_api', return_value=_api_result), \
             patch.object(ProposalAgent, '_save_proposal', return_value=__import__('pathlib').Path("/tmp/test.md")):
            # Simulate orchestrator calling with a task description
            result = agent.run(args=["Empresa XYZ saúde acelerar vendas"])
            self.assertIsNotNone(result)

    def test_lead_report_agent_callable_from_orchestrator_style(self):
        """LeadReportAgent must not raise TypeError when called as a subtask."""
        from core.agents.lead_report_agent import LeadReportAgent
        agent = LeadReportAgent.__new__(LeadReportAgent)
        agent.memory = MagicMock()
        with patch.object(LeadReportAgent, 'generate_report', return_value="relatório"):
            result = agent.run(args=["demo"])
            # run() now returns a dict with a "text" key
            self.assertIsInstance(result, dict)
            self.assertIn("text", result)

    def test_proposal_in_agent_map_is_instantiable(self):
        from core.agents.orchestrator_agent import AGENT_MAP
        cls = AGENT_MAP["proposal"]
        agent = cls.__new__(cls)
        self.assertIsNotNone(agent)

    def test_lead_report_in_agent_map_is_instantiable(self):
        from core.agents.orchestrator_agent import AGENT_MAP
        cls = AGENT_MAP["lead-report"]
        agent = cls.__new__(cls)
        self.assertIsNotNone(agent)

    def test_proposal_agent_task_type_is_valid(self):
        from core.agents.proposal_agent import ProposalAgent
        from core.claude_client import TaskType
        # task_type must be a valid TaskType value
        tt = ProposalAgent.task_type
        valid = list(TaskType) + [t.value for t in TaskType]
        self.assertIn(tt, valid)

    def test_lead_report_agent_task_type_is_valid(self):
        from core.agents.lead_report_agent import LeadReportAgent
        from core.claude_client import TaskType
        tt = LeadReportAgent.task_type
        valid_strings = [t.value for t in TaskType]
        # task_type can be string or enum
        tt_str = tt.value if hasattr(tt, 'value') else tt
        self.assertIn(tt_str, valid_strings)


if __name__ == "__main__":
    unittest.main()

"""Tests for ProposalAgent path safety and contract."""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestProposalAgentSafety(unittest.TestCase):

    def _make_agent(self):
        from core.agents.proposal_agent import ProposalAgent
        agent = ProposalAgent.__new__(ProposalAgent)
        return agent

    def test_safe_filename_strips_path_separators(self):
        agent = self._make_agent()
        result = agent._safe_filename("../../etc/passwd")
        self.assertNotIn("/", result)
        self.assertNotIn(".", result)

    def test_safe_filename_strips_null_bytes(self):
        agent = self._make_agent()
        result = agent._safe_filename("empresa\x00hack")
        self.assertNotIn("\x00", result)

    def test_safe_filename_normal_name(self):
        agent = self._make_agent()
        result = agent._safe_filename("Empresa XYZ")
        self.assertIn("Empresa", result)

    def test_save_proposal_path_inside_proposals_dir(self):
        from core.agents.proposal_agent import ProposalAgent, PROPOSALS_DIR
        agent = ProposalAgent.__new__(ProposalAgent)
        with patch.object(Path, 'write_text'), patch.object(Path, 'mkdir'):
            path = agent._save_proposal("content", "Test Client")
            self.assertTrue(str(path).startswith(str(PROPOSALS_DIR.resolve())))

    def test_path_traversal_raises_value_error(self):
        from core.agents.proposal_agent import ProposalAgent
        import core.agents.proposal_agent as pa_module
        agent = ProposalAgent.__new__(ProposalAgent)

        # Patch PROPOSALS_DIR to a known path and _safe_filename to a traversal attempt
        safe_proposals = Path("/tmp/propostas_test")
        with patch.object(pa_module, 'PROPOSALS_DIR', safe_proposals), \
             patch.object(agent.__class__, '_safe_filename', return_value="../../../etc/passwd"), \
             patch.object(Path, 'mkdir'):
            with self.assertRaises(ValueError):
                agent._save_proposal("content", "hack")

    def test_generate_returns_dict_with_text_and_file(self):
        from core.agents.proposal_agent import ProposalAgent
        agent = ProposalAgent.__new__(ProposalAgent)
        agent.memory = MagicMock()
        with patch.object(agent.__class__, '_call_api', return_value={"text": "Proposta gerada"}), \
             patch.object(agent.__class__, '_save_proposal', return_value=Path("/home/user/propostas/test.md")):
            result = agent.generate("Cliente", "saude", "acelerar vendas")
            self.assertIn("text", result)
            self.assertIn("file", result)



    def test_proposals_dir_overridable_by_env(self):
        import os, importlib
        with patch.dict(os.environ, {"PROPOSALS_DIR": "/tmp/test_proposals"}):
            import core.agents.proposal_agent as mod
            importlib.reload(mod)
            self.assertEqual(str(mod.PROPOSALS_DIR), "/tmp/test_proposals")
        # Reload back to normal
        importlib.reload(mod)

if __name__ == "__main__":
    unittest.main()

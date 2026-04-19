"""Smoke tests: make_client() is used in API and workflow entrypoints."""
import importlib, unittest

class TestEntrypointsMakeClient(unittest.TestCase):
    def test_api_app_uses_make_client(self):
        import ast, pathlib
        src = pathlib.Path("api/app.py").read_text()
        tree = ast.parse(src)
        calls = [n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn("make_client", calls, "api/app.py must call make_client()")

    def test_workflow_engine_uses_make_client(self):
        import ast, pathlib
        src = pathlib.Path("workflows/engine.py").read_text()
        tree = ast.parse(src)
        # Check for make_client call (may be attribute or name)
        found = any(
            isinstance(n, ast.Call) and (
                (isinstance(n.func, ast.Name) and n.func.id == "make_client") or
                (isinstance(n.func, ast.Attribute) and n.func.attr == "make_client")
            )
            for n in ast.walk(tree)
        )
        self.assertTrue(found, "workflows/engine.py must call make_client()")

if __name__ == "__main__":
    unittest.main()

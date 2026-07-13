from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ImportBoundaryTest(unittest.TestCase):
    def test_domain_has_no_application_or_infrastructure_imports(self) -> None:
        forbidden = ("qcm_application", "qcm_infrastructure", "qcm_api", "qcm_worker")
        for source in (ROOT / "packages" / "domain" / "src").rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                module = None
                if isinstance(node, ast.ImportFrom):
                    module = node.module
                elif isinstance(node, ast.Import):
                    module = node.names[0].name
                if module:
                    self.assertFalse(module.startswith(forbidden), f"{source} imports {module}")


if __name__ == "__main__":
    unittest.main()

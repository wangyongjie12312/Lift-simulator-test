"""Every third-party import must be declared.

This exists because httpx was added to the code and not to requirements.txt:
it happened to be installed here, so 31 tests passed and the first clean
install failed. Tests run in the dev environment and cannot see a missing
dependency - only a check like this can.
"""
import ast, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = {"api", "core", "ui", "jobs", "tests", "app", "serve"}
#: modules imported by name from a sibling file inside the same package - the
#: physics self-tests fall back to a flat import when run as __main__
SIBLING_OK = {p.stem for p in (ROOT / "core" / "physics").glob("*.py")}


def _top_level_imports():
    out = {}
    for f in ROOT.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    out.setdefault(a.name.split(".")[0], set()).add(f.name)
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                out.setdefault(n.module.split(".")[0], set()).add(f.name)
    return out


class TestDependencies(unittest.TestCase):
    def test_all_third_party_imports_are_in_requirements(self):
        declared = {l.split(">=")[0].split("==")[0].split("[")[0].strip().lower()
                    for l in (ROOT / "requirements.txt").read_text().splitlines()
                    if l.strip() and not l.startswith("#")}
        missing = {}
        for mod, files in _top_level_imports().items():
            if (mod in sys.stdlib_module_names or mod in LOCAL
                    or mod in SIBLING_OK or mod == "__future__"):
                continue
            if mod.lower() not in declared:
                missing[mod] = sorted(files)
        self.assertEqual(missing, {},
                         f"imported but not in requirements.txt: {missing}")


if __name__ == "__main__":
    unittest.main()

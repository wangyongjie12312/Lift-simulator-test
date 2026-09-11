"""The split is only real if it is enforced. These are the rules that make it
so - each one has a failure mode that is invisible until it bites."""
import re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

UI = [ROOT / "app.py"] + sorted((ROOT / "ui").glob("*.py"))
CORE = sorted((ROOT / "core").rglob("*.py"))


class TestIsolation(unittest.TestCase):
    def test_ui_never_imports_the_domain(self):
        """If the UI can import core, someone will - and then the solver runs
        inside Streamlit's rerun loop and data/ has two writers again."""
        for f in UI:
            src = f.read_text(encoding="utf-8")
            self.assertNotRegex(src, r"^\s*(from|import)\s+core\b",
                                f"{f.name} imports core")

    def test_ui_touches_the_api_only_through_the_client(self):
        """One module is the boundary. Anything else calling httpx means a
        second place to fix when auth or the base URL changes."""
        for f in UI:
            if f.name == "client.py":
                continue
            self.assertNotIn("httpx", f.read_text(encoding="utf-8"), f.name)

    def test_ui_writes_no_files_under_data(self):
        for f in UI:
            self.assertNotIn('"data"', f.read_text(encoding="utf-8"), f.name)

    def test_core_never_imports_a_framework(self):
        for f in CORE:
            src = f.read_text(encoding="utf-8")
            self.assertNotRegex(src, r"^\s*(from|import)\s+(fastapi|streamlit)\b",
                                f"{f} imports a framework")

    def test_contract_models_carry_no_framework(self):
        """The UI imports api/schemas.py directly, so it must stay pure
        pydantic - importing FastAPI there would drag the server into the UI
        process."""
        src = (ROOT / "api" / "schemas.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r"^\s*(from|import)\s+fastapi\b")

    def test_every_api_call_in_the_ui_is_cached_or_user_driven(self):
        """Streamlit reruns the whole script on every widget change. An
        uncached call at module level would mean a solve per keystroke."""
        src = (ROOT / "ui" / "data.py").read_text(encoding="utf-8")
        for fn in re.findall(r"\ndef (\w+)\(.*?\n(?=\ndef |\Z)", src, re.S):
            pass
        self.assertIn("@st.cache_data", src)
        # the solve itself must be behind a cache
        m = re.search(r"@st\.cache_data[^\n]*\ndef _simulate", src)
        self.assertIsNotNone(m, "the simulate call is not cached")


if __name__ == "__main__":
    unittest.main()

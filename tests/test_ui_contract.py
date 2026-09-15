"""A few facts about the Streamlit UI that are easy to break by accident and
have no other test to catch them."""
import re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ui import auth, dialogs, help_text, theme, views


class TestUiContract(unittest.TestCase):
    def test_five_case_ceiling_with_a_second_encoding(self):
        """Five is where colours still separate on white. Beyond colour, each
        case must also carry a dash pattern and a letter."""
        self.assertEqual(theme.MAX_CASES, 5)
        tags = [t for t, _, _ in theme.CASE_STYLE]
        dashes = [d for _, _, d in theme.CASE_STYLE]
        self.assertEqual(len(set(tags)), 5)
        self.assertEqual(len(set(dashes)), 5)

    def test_only_implemented_profiles_are_offered(self):
        self.assertEqual(views.PROFILES, ["Safelink formula", "Constant"])

    def test_idle_timeout_is_five_minutes_with_warning(self):
        self.assertEqual(auth.IDLE_S, 300)
        self.assertEqual(auth.WARN_S, 30)

    def test_the_pop_outs_are_modals(self):
        """A new browser tab would be a new Streamlit session: signed out, and
        knowing nothing about the current selection. The reference UI used
        modals for these anyway."""
        for fn in ("unit_details", "help_doc", "save_case", "load_case",
                   "sign_out"):
            self.assertTrue(hasattr(dialogs, fn), fn)
        src = (ROOT / "ui" / "dialogs.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("@st.dialog"), 5)

    def test_help_keeps_its_two_placeholders(self):
        """Terminology and the calculation basis have to come from Safelink.
        A plausible guess in a reference document is worse than an admitted
        gap, so these must stay marked."""
        self.assertEqual(set(help_text.PLACEHOLDERS),
                         {"3 · Terminology", "7 · Technical basis"})
        for title, body in help_text.SECTIONS:
            if title in help_text.PLACEHOLDERS:
                self.assertIsNone(body)

    def test_charts_carry_major_and_minor_ticks(self):
        """An axis with no reference lines makes the chart decorative."""
        from ui import charts
        self.assertTrue(charts.AXIS["showgrid"])
        self.assertEqual(charts.AXIS["ticks"], "outside")
        self.assertEqual(charts.AXIS["minor"]["ticks"], "outside")
        self.assertTrue(charts.AXIS["minor"]["showgrid"])

    def test_brand_logo_is_not_recoloured(self):
        """The supplied wordmark is white + yellow, for a dark background. It
        goes on a dark chip rather than being repainted."""
        figs = ROOT / "web" / "figures"
        for f in ("safelink_logo.png", "safelink_logo_chip.png",
                  "safelink_mark.png"):
            self.assertTrue((figs / f).exists(), f)

    def test_showcase_images_exist(self):
        for img, *_ in auth.SLIDES:
            self.assertTrue((auth.SHOWCASE_DIR / img).exists(), img)

    def test_sign_out_clears_the_session(self):
        """The next person must not find the previous one's case on screen."""
        src = (ROOT / "ui" / "auth.py").read_text(encoding="utf-8")
        m = re.search(r"def sign_out\(\).*?st\.rerun\(\)", src, re.S)
        self.assertIsNotNone(m)
        self.assertIn("del st.session_state[k]", m.group(0))

    def test_add_to_compare_is_gated_on_a_fresh_result(self):
        """A case is inputs together with the results they produced, so the
        button compares the request that produced the result against the one
        on screen. No bookkeeping, and a reload cannot lose it."""
        src = (ROOT / "ui" / "views.py").read_text(encoding="utf-8")
        self.assertIn('st.session_state.get("result_req") == req', src)
        self.assertIn("disabled=not fresh", src)

    def test_request_is_built_from_the_api_models(self):
        """One definition of the contract. Hand-built dicts drift within a
        month."""
        src = (ROOT / "ui" / "views.py").read_text(encoding="utf-8")
        self.assertIn("from api.schemas import", src)
        self.assertIn("SimRequest(", src)


if __name__ == "__main__":
    unittest.main()


class TestRawHtmlDiscipline(unittest.TestCase):
    """st.markdown still runs the Markdown parser even with
    unsafe_allow_html, and on some versions that splits a one-line <div> into
    separate blocks - a flex row silently becomes three stacked lines, which
    is exactly what happened to the user card. st.html has no parser in the
    way, so every raw-HTML render must go through it."""

    #: theme.py is the exception - injecting a <style> block is what it is for
    FILES = ["app.py", "ui/chrome.py", "ui/views.py", "ui/auth.py",
             "ui/dialogs.py"]

    def test_no_unsafe_allow_html_anywhere(self):
        for f in self.FILES:
            src = (ROOT / f).read_text(encoding="utf-8")
            self.assertNotIn("unsafe_allow_html", src, f)

    def test_layout_uses_inline_styles_not_injected_classes(self):
        """An injected stylesheet is one more thing that can go missing. The
        title row, the user card and the KPI tiles carry their own styles."""
        for f in ("ui/chrome.py", "ui/views.py"):
            src = (ROOT / f).read_text(encoding="utf-8")
            self.assertNotIn('class="band-hd"', src, f)
            self.assertNotIn('class="kpi', src, f)
            self.assertNotIn('class="usercard"', src, f)


class TestDialogsAreOpenedTheSameWay(unittest.TestCase):
    """Help and Sign out always rendered as modals; Save, Load and Unit
    details rendered inline on the user's Streamlit. The difference was that
    the working two set a flag and let the run continue, while the others
    called st.rerun() first - which hands the dialog to a run no interaction
    triggered. All five now share one shape."""

    def test_no_dialog_takes_arguments(self):
        src = (ROOT / "ui" / "dialogs.py").read_text(encoding="utf-8")
        for fn in ("unit_details", "help_doc", "save_case", "load_case",
                   "sign_out"):
            self.assertIn(f"def {fn}() -> None:", src, fn)

    def test_buttons_do_not_rerun_before_opening_a_dialog(self):
        """A flag plus st.rerun() opens the dialog in the wrong run."""
        src = (ROOT / "ui" / "views.py").read_text(encoding="utf-8")
        for block in re.findall(r"st\.session_state\.dialog[^\n]*\n(\s*[^\n]*)",
                                src):
            self.assertNotIn("st.rerun()", block)

    def test_every_dialog_is_dispatched_from_the_top_level(self):
        """Opening one from inside `with st.sidebar:` leaves its placement up
        to the Streamlit version."""
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        tail = src[src.index("# ---- dialogs"):]
        for fn in ("help_doc", "sign_out", "unit_details", "save_case",
                   "load_case"):
            self.assertIn(f"dialogs.{fn}()", tail, fn)
        # nothing in the sidebar block may call a dialog directly
        head = src[:src.index("chrome.title_row")]
        self.assertNotIn("dialogs.", head)

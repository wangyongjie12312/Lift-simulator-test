"""The sea-temperature profile is the one column the solver really computes,
so it must actually respond to the Environment inputs - end to end, not just
in the physics module. This is the regression this test exists for."""
import re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.main import app
from api import state
from core.physics import sea_temperature as st

UNIT = "X-4500 450/700-001"


class TestSeaTempEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(app); cls.c.__enter__(); state.warm_up()

    @classmethod
    def tearDownClass(cls):
        cls.c.__exit__(None, None, None)

    def run_env(self, **env):
        r = self.c.post("/api/simulate", json={
            "unit_name": UNIT, "depth_steps": 25, "client_inputs": env})
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()["columns"]
        return list(zip(d["depth_m"], d["T_c"]))

    def test_formula_decreases_with_depth(self):
        p = [t for d, t in self.run_env(sea_temp_profile="Safelink formula")
             if d > 0]
        self.assertTrue(all(a >= b for a, b in zip(p, p[1:])), "not monotonic")
        self.assertLess(p[-1], 6.0)          # deep water is cold

    def test_surface_temperature_moves_the_whole_profile(self):
        warm = self.run_env(sea_temp_profile="Safelink formula", surface_temp_c=25)
        cold = self.run_env(sea_temp_profile="Safelink formula", surface_temp_c=8)
        deep = [(a[1], b[1]) for a, b in zip(warm, cold) if a[0] > 0]
        self.assertTrue(all(w > c for w, c in deep), "profile ignored the surface")

    def test_constant_profile_is_constant_below_the_waterline(self):
        below = [t for d, t in self.run_env(sea_temp_profile="Constant",
                                            surface_temp_c=12) if d > 0]
        self.assertTrue(all(abs(t - 12.0) < 1e-9 for t in below))

    def test_air_temperature_used_above_the_waterline(self):
        above = [t for d, t in self.run_env(sea_temp_profile="Safelink formula",
                                            air_temp_c=17, surface_temp_c=25)
                 if d <= 0]
        self.assertTrue(above and all(abs(t - 17.0) < 1e-9 for t in above))

    def test_unimplemented_profile_is_refused_not_silently_swapped(self):
        r = self.c.post("/api/simulate", json={
            "unit_name": UNIT, "client_inputs": {"sea_temp_profile": "User table"}})
        self.assertEqual(r.status_code, 422)

    def test_reference_ui_port_matches_python(self):
        """docs/reference-ui.html is the design reference the Streamlit UI was
        built from, and it carries its own copy of this formula. Keep the two
        from drifting while it is still the spec people read."""
        js = (ROOT / "docs" / "reference-ui.html").read_text(encoding="utf-8")
        m = re.search(r"const ST = \{ASYM:(-?[\d.]+), SLOPE:(-?[\d.]+), "
                      r"OFFSET:(-?[\d.]+), DEEP:([\d.e-]+)\}", js)
        self.assertIsNotNone(m, "constants not found in docs/reference-ui.html")
        for got, want in zip(m.groups(), (st.T_ASYMPTOTE, st.THERMOCLINE_SLOPE,
                                          st.THERMOCLINE_OFFSET, st.DEEP_COEFF)):
            self.assertAlmostEqual(float(got), want, places=12)


if __name__ == "__main__":
    unittest.main()

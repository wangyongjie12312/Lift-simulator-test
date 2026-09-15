"""/simulate: shape, hashing, and the two ways it should refuse."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from api import state

UNIT = "X-4500 325/400-001…2"


class TestSimulate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(app)
        cls.c.__enter__()          # runs lifespan, so the registry is loaded
        state.warm_up()            # ...and wait for it rather than race it

    @classmethod
    def tearDownClass(cls):
        cls.c.__exit__(None, None, None)

    def test_shape(self):
        r = self.c.post("/api/simulate",
                        json={"unit_name": UNIT, "depth_steps": 41})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["n_steps"], 41)
        self.assertTrue(d["placeholder"])          # still the stand-in engine
        self.assertEqual(len(d["columns"]["depth_m"]), 41)
        self.assertEqual(len(d["columns"]["T_c"]), 41)
        self.assertIn("suitable", d["verdict"])

    def test_hash_tracks_inputs(self):
        a = self.c.post("/api/simulate", json={"unit_name": UNIT}).json()
        b = self.c.post("/api/simulate", json={"unit_name": UNIT}).json()
        c = self.c.post("/api/simulate", json={
            "unit_name": UNIT, "safelink_inputs": {"p_sz_barg": 90.0}}).json()
        self.assertEqual(a["input_hash"], b["input_hash"])
        self.assertNotEqual(a["input_hash"], c["input_hash"])

    def test_unknown_unit_404(self):
        r = self.c.post("/api/simulate", json={"unit_name": "no such unit"})
        self.assertEqual(r.status_code, 404)

    def test_depth_range_rejected(self):
        r = self.c.post("/api/simulate", json={
            "unit_name": UNIT,
            "client_inputs": {"start_depth_m": 100, "final_depth_m": 50}})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()

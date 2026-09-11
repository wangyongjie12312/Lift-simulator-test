"""Registry rules that must hold in the API, not just in the UI."""
import shutil, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from api import state
from core.registry import DEFAULT_PATH

UNIT = "X-4500 325/400-001…2"


class TestUnits(unittest.TestCase):
    """These write to data/units.json, so the file is saved and put back."""

    @classmethod
    def setUpClass(cls):
        cls.backup = DEFAULT_PATH.read_bytes()
        cls.c = TestClient(app); cls.c.__enter__(); state.warm_up()

    @classmethod
    def tearDownClass(cls):
        cls.c.__exit__(None, None, None)
        DEFAULT_PATH.write_bytes(cls.backup)
        state.warm_up()

    def test_list_hides_deleted(self):
        r = self.c.get("/api/units")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(all(u["state"] == 1 for u in r.json()))

    def test_variant_does_not_touch_the_catalogue_unit(self):
        before = self.c.get("/api/units").json()
        base = next(u for u in before if u["name"] == UNIT)
        r = self.c.post("/api/units/variant",
                        json={"base_name": UNIT, "changes": {"l_s": 5.0}})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["origin"], "variant")
        self.assertEqual(r.json()["params"]["l_s"], 5.0)
        after = self.c.get("/api/units").json()
        self.assertEqual(next(u for u in after if u["name"] == UNIT)
                         ["params"]["l_s"], base["params"]["l_s"])

    def test_delete_is_soft(self):
        name = self.c.post("/api/units", json={
            "name": "TMP-1 10/10-999", "params": {"l_s": 1.0}}).json()["name"]
        self.assertEqual(self.c.delete("/api/units", params={"name": name}).status_code, 200)
        names = [u["name"] for u in self.c.get("/api/units").json()]
        self.assertNotIn(name, names)
        all_names = [u["name"] for u in
                     self.c.get("/api/units?include_deleted=true").json()]
        self.assertIn(name, all_names)      # record kept, old cases resolve


if __name__ == "__main__":
    unittest.main()

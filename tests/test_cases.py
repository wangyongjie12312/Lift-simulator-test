"""Cases must not collide between users - the point of the whole layout."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cases


class TestCaseStore(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_same_name_different_owners(self):
        a = cases.save_case("wang", "Test 1", {"p": 1}, root=self.root)
        b = cases.save_case("oda", "Test 1", {"p": 2}, root=self.root)
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(len(cases.list_cases("wang", root=self.root)), 1)
        self.assertEqual(
            cases.load_case("oda", b["id"], root=self.root)["inputs"]["p"], 2)

    def test_same_name_same_owner_is_two_cases(self):
        cases.save_case("wang", "Test 1", {"p": 1}, root=self.root)
        cases.save_case("wang", "Test 1", {"p": 2}, root=self.root)
        self.assertEqual(len(cases.list_cases("wang", root=self.root)), 2)

    def test_update_keeps_id_and_created(self):
        a = cases.save_case("wang", "A", {"p": 1}, root=self.root)
        b = cases.save_case("wang", "A2", {"p": 9}, case_id=a["id"],
                            root=self.root)
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(a["created_utc"], b["created_utc"])
        self.assertEqual(len(cases.list_cases("wang", root=self.root)), 1)

    def test_path_traversal_rejected(self):
        for bad in ("../etc", "a/b", "", "WANG/../root"):
            with self.assertRaises(cases.CaseError):
                cases.save_case(bad, "x", {}, root=self.root)
        with self.assertRaises(cases.CaseError):
            cases.load_case("wang", "../../units", root=self.root)


if __name__ == "__main__":
    unittest.main()

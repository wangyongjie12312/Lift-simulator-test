"""Two people solving at once must get the same answers as one person
solving twice. Guards against anyone adding module-level mutable state to
core/ - that is the one way concurrent solves could contaminate each other."""
import sys, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import state
from core.registry import load_units
from core.schema import CaseInputs


class TestConcurrentSolves(unittest.TestCase):
    def test_parallel_matches_serial(self):
        units = load_units()
        cases = [CaseInputs(unit_name=units[0].name, p_sz_barg=p,
                            depth_steps=61) for p in (80.0, 85.0, 90.0, 95.0)]
        serial = [state.engine.simulate(units[0], c).P_sz_barg for c in cases]
        with ThreadPoolExecutor(max_workers=4) as ex:
            parallel = list(ex.map(
                lambda c: state.engine.simulate(units[0], c).P_sz_barg, cases))
        self.assertEqual(serial, parallel)
        self.assertNotEqual(serial[0], serial[-1])   # inputs really do differ


if __name__ == "__main__":
    unittest.main()

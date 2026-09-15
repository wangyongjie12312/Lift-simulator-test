"""python tests/run_all.py - everything, including the physics self-tests."""
import subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PHYSICS = ["sea_temperature", "calculate_pressure", "gas_transfer",
           "select_adjustment_mode_xs", "peng_robinson_isothermal_moles",
           "booster_energy_consumption"]

if __name__ == "__main__":
    ok = True
    for m in PHYSICS:                       # each module self-tests on __main__
        r = subprocess.run([sys.executable, "-m", f"core.physics.{m}"],
                           cwd=ROOT, capture_output=True, text=True)
        print(f"physics/{m:<34} {'PASS' if r.returncode == 0 else 'FAIL'}")
        ok &= r.returncode == 0
        if r.returncode:
            print(r.stdout[-800:], r.stderr[-800:])

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if (ok and res.wasSuccessful()) else 1)

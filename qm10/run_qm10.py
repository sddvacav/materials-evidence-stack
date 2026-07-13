from __future__ import annotations

from pathlib import Path

here = Path(__file__).resolve().parent
source_path = here / "build_qm10.py"
patched_path = here / "build_qm10_patched.py"
source = source_path.read_text(encoding="utf-8")
start = source.index("tests=f'''")
end = source.index('write_text("tests/__init__.py"', start)
replacement = '''tests="""import unittest
from analysis_code.qm10_analysis import *

class T(unittest.TestCase):
    def test_mass(self):
        self.assertTrue(4.50 < mass_rom({"Ti":97.6,"TiB2":2.4},{"Ti":4.506,"TiB2":4.52}) < 4.52)
    def test_volume(self):
        value = volume_rom({"Ti":87.12,"TiC":12.88},{"Ti":4.506,"TiC":4.93})
        self.assertTrue(4.55 < value < 4.57)
    def test_specific(self):
        self.assertAlmostEqual(specific(1000,5),200)
    def test_pct(self):
        self.assertAlmostEqual(pct(110,100),10)
    def test_pareto(self):
        self.assertTrue(dominates(4.627,1147,4.630,1090))
    def test_not_robust(self):
        self.assertFalse(robust_density(4.627,.01,4.630,.01))
    def test_heavy_penalty(self):
        rho = mass_rom({"Ti":82.54,"Al":5.9,"Sn":4.0,"Zr":3.5,"Mo":0.5,"Nb":0.3,"Ta":2.0,"Si":0.4,"W":0.8,"C":0.06},{"Ti":4.506,"Al":2.70,"Sn":7.31,"Zr":6.52,"Mo":10.28,"Nb":8.57,"Ta":16.69,"Si":2.329,"W":19.25,"C":2.267})
        cf = mass_rom({"Ti":85.34,"Al":5.9,"Sn":4.0,"Zr":3.5,"Mo":0.5,"Nb":0.3,"Si":0.4,"C":0.06},{"Ti":4.506,"Al":2.70,"Sn":7.31,"Zr":6.52,"Mo":10.28,"Nb":8.57,"Si":2.329,"C":2.267})
        self.assertGreater(rho-cf,0)
    def test_ductility_utility(self):
        c={"UTS":914,"YS":844,"E":110,"EL":10,"density":4.54}
        t={"UTS":1234,"YS":1160.6,"E":130.5,"EL":1.35,"density":4.5564}
        self.assertLess(utility(c,t,{"UTS":.25,"YS":.15,"E":.1,"EL":.4,"density":.1}),0)

if __name__=="__main__":
    unittest.main()
"""
'''
patched = source[:start] + replacement + source[end:]
patched_path.write_text(patched, encoding="utf-8")
namespace = {"__file__": str(patched_path), "__name__": "__main__"}
exec(compile(patched, str(patched_path), "exec"), namespace)

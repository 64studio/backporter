import unittest

from data import *
from backporter.Backporter            import Backporter
from backporter.Models                import *
from backporter.BackporterConfig      import BackporterConfig
from backporter.BackporterScheduler   import BackporterScheduler

#from backporter.Backporterd import Backporterd

class TestSequenceFunctions(unittest.TestCase):
    
    def test_workspace(self):
        for pkg in pkgs_test:
            Backporter().add(pkg[0], 'etch')

        Backporter().update()

if __name__ == '__main__':
    unittest.main()

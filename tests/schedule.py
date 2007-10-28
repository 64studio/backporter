import unittest

from backporter.Backporter            import Backporter
from backporter.BackporterConfig      import BackporterConfig
from backporter.BackporterScheduler   import BackporterScheduler

#from backporter.Backporterd import Backporterd

class TestSequenceFunctions(unittest.TestCase):
    
    def _backporterd(self):
        Backporterd()

    def test_workspace(self):
        Backporter().update()
        Backporter().schedule()

if __name__ == '__main__':
    unittest.main()

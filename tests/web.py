import unittest

from backporter.Backporter            import Backporter
from backporter.Models                import *
from backporter.BackporterConfig      import BackporterConfig
from backporter.BackporterWeb         import *

#from backporter.Backporterd import Backporterd

class TestSequenceFunctions(unittest.TestCase):
    
    def test_web(self):
        print "ok"
#        RequestIndex().GET('etch')

if __name__ == '__main__':
    unittest.main()

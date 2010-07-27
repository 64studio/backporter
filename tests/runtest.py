#!/usr/bin/env python2.6

import sys 
 
sys.path.insert(0, "..") 
sys.path.insert(0, ".") 

import unittest
from TestModels     import *
from TestBackporter import TestBackporter

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPackage)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestJob))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBackport))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBackporter))
    unittest.TextTestRunner(verbosity=2).run(suite)

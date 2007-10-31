#!/usr/bin/env python2.5

import sys 
 
sys.path.insert(0, "..") 
sys.path.insert(0, ".") 

import unittest
from TestModels import TestModels

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestModels)
#    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDistribution))
    unittest.TextTestRunner(verbosity=2).run(suite)

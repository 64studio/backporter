import random
import unittest
import os

from backporter.BackporterConfig      import BackporterConfig
from backporter.Database    import Database
from backporter.Logger      import Logger
from backporter.Models      import *
from backporter.Backporter  import Backporter

#from backporter.Backporterd import Backporterd

class TestSequenceFunctions(unittest.TestCase):
    
    def _backporterd(self):
        Backporterd()

    def test_all(self):
        self._test_models()
        self._test_workspace()

    def _test_workspace(self):
        Backporter().update()
        Backporter().schedule()

    def _test_models(self):
        self._test_dist()
        self._test_backport()
        self._test_source()

    def _test_dist(self):
        etch = ('etch',
                DistType.Released.Value,
                'http://ftp.it.debian.org/debian',
                'main contrib non-free')
        sid  = ('sid', 
                DistType.Bleeding.Value,
                'http://ftp.it.debian.org/debian',
                'main contrib non-free')
        Backporter().dist_add(etch[0], etch[1], etch[2], etch[3])
        Backporter().dist_add(sid[0], sid[1], sid[2], sid[3])
        Backporter().dist_update(etch[0], etch[1], etch[2], 'main contrib')

    def _test_backport(self):
        pkgs = [('libgig', 0, None),
                ('liblscp', 0, None),
                ('bootsplash', BackportStatus.AutoUpdate.Value, None),
                ('sysv-rc-bootsplash', BackportStatus.AutoUpdate.Value, None)]

        for pkg in pkgs:
            Backporter().backport_add(pkg[0], pkg[1], pkg[2])

    def _test_source(self):
        libgig  = ('libgig', 'etch', '0.1')
        liblscp = ('liblscp', 'sid', '0.2')
        Backporter().source_update(libgig[0], libgig[1], '0.1.1')

if __name__ == '__main__':
    unittest.main()

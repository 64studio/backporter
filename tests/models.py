import random
import unittest
import os

from data import *
from backporter.BackporterConfig      import BackporterConfig
from backporter.Models      import *
from backporter.Backporter  import Backporter

#from backporter.Backporterd import Backporterd

class TestSequenceFunctions(unittest.TestCase):
    
    def test_models(self):
        self._test_source()
        self._test_dist()
        self._test_backport()
        self._test_package()
        self._test_job()

    def _test_dist(self):
        for dist in dists:
            Backporter().dist_add(dist[0], dist[1], dist[2], dist[3])
        etch  = dists[0]
        gutsy = dists[3]
        Backporter().dist_update(etch[0], etch[1], etch[2], 'main contrib')
        Backporter().dist_remove(gutsy[0])

    def _test_backport(self):

        for bkp in bkps:
            Backporter().backport_add(bkp[0], bkp[1], bkp[2])
        Backporter().backport_remove('qtractor')
        Backporter().backport_remove('wine')
        Backporter().backport_remove('jack')

    def _test_source(self):
        libgig  = bkps[0]
        Backporter().source_update(libgig[0], libgig[1], '0.1.1')


    def _test_package(self):
        p = Package()
        for pkg in pkgs:
            p.id       = pkg[0]
            p.name     = pkg[1]
            p.version  = pkg[2]
            p.priority = pkg[3]
            p.insert()
        i = 1
        for p in Package().select():
            self.assertEqual(p.id, i)
            i += 1
        self.assertEqual(len(Package().select()), 2)
        p = Package('libgig','0.1')
        p.name = "foo"
        p.update()
        q = Package('foo','0.1')
        self.assertEqual(p.name, "foo")
        for p in Package().select():
            p.delete()
        self.assertEqual(len(Package().select()), 0)

    def _test_job(self):
        p = Package()
        for pkg in pkgs:
            p.id       = pkg[0]
            p.name     = pkg[1]
            p.version  = pkg[2]
            p.priority = pkg[3]
            p.insert()
        j = Job()
        for job in jobs:
            j.id             = job[0]
            j.status         = job[1]
            j.mailto         = job[2]
            j.package_id     = job[3]
            j.dist           = job[4]
            j.arch           = job[5]
            j.creation_date  = job[6]
            j.status_changed = job[7]
            j.build_end      = job[8]
            j.build_start    = job[9]
            j.host           = job[10]
            j.insert()
        self.assertEqual(len(Job().select()), 2)
        j = Job(2)
        j.mailto = "foo"
        j.update()
        k = Job(2)
        self.assertEqual(k.mailto, "foo")
        self.assertEqual(len(Job().select(package_id=1)), 1)
        self.assertEqual(len(Job.join('etch')), 2)
        self.assertEqual(len(Job.join('etch','libgig')), 1)
        for j in Job().select():
            j.delete()
        self.assertEqual(len(Job().select()), 0)

if __name__ == '__main__':
    unittest.main()

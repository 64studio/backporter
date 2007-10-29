import random
import unittest
import os

from backporter.BackporterConfig      import BackporterConfig
from backporter.Models      import *
from backporter.Backporter  import Backporter
from data import *

class TestSequenceFunctions(unittest.TestCase):
    
    def test_64studio(self):
        for dist in dists:
            Backporter().dist_add(dist[0], dist[1], dist[2], dist[3])
        for pkg in pkgs_many:
            Backporter().backport_add(pkg[0], pkg[2], None)
        i = 1
        for pkg in pkgs_many:
            Backporter().package_add(pkg[0], pkg[1], 1)
            Backporter().job_add(i,'etch','i386')
            Backporter().job_add(i,'etch','amd64')
            i += 1
        for j in Job.select(dist='etch'):
            j.status = 1000
            j.update()
            p = Package(id=j.package_id)
            if p.name == "fst" and j.arch == "amd64":
                j.delete()
        Backporter().backport_update('fst',options={'arch':'i386'})

if __name__ == '__main__':
    unittest.main()

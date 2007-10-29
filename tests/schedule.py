import unittest

from data import *
from backporter.Backporter            import Backporter
from backporter.Models                import *
from backporter.BackporterConfig      import BackporterConfig
from backporter.BackporterScheduler   import BackporterScheduler

#from backporter.Backporterd import Backporterd

class TestSequenceFunctions(unittest.TestCase):
    
    def test_workspace(self):
        for dist in dists:
            Backporter().dist_add(dist[0], dist[1], dist[2], dist[3])
        for bkp in bkps:
            Backporter().backport_add(bkp[0], bkp[1], bkp[2])
#        i = 1
#        for pkg in pkgs:
#            Backporter().package_add(pkg[0], pkg[1], 1)
#            Backporter().job_add(i,'etch','i386')
#            Backporter().job_add(i,'etch','amd64')
#            i += 1
        for j in Job.select():
            j.status = 1000
            j.update()
        Backporter().update()
        Backporter().schedule()

if __name__ == '__main__':
    unittest.main()

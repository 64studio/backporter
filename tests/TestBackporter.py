#!/usr/bin/env python2.5
import sys  
  
sys.path.insert(0, "..")  
sys.path.insert(0, ".")  

import unittest
import types
import os

from pysqlite2                  import dbapi2 as sqlite
from rebuildd.RebuilddConfig    import RebuilddConfig
from rebuildd.JobStatus         import JobStatus
from backporter.Database        import Database
from backporter.Models          import *
from backporter.Backporter      import Backporter
from backporter.BackporterError import BackporterError

class TestBackporter(unittest.TestCase):

    def setUp(self):
	Database().clean()
        RebuilddConfig().set('build', 'archs', 'i386 amd64')

        self.backports = (('alsa-driver',   'etch',  BackportPolicy.Smart.Value),
                          ('alsa-driver',   'gutsy', BackportPolicy.Smart.Value),
                          ('alsa-firmware', 'etch',  BackportPolicy.Smart.Value),
                          ('alsa-firmware', 'gutsy', BackportPolicy.Smart.Value))

        for backport in self.backports:
            Backporter().add(backport[0], backport[1])
            Backporter().set(backport[0], backport[1], 'policy', backport[2])

    def test_add(self):
        for backport in self.backports:
            b = Backport(backport[0], backport[1])
            self.assertEqual(b.pkg,  backport[0])
            self.assertEqual(b.dist, backport[1])

    def test_set(self):
        for backport in self.backports:
            b = Backport(backport[0], backport[1])
            self.assertEqual(b.policy,  backport[2])

    def test_schedule(self):

        Backporter().update()
        Backporter().schedule()

        status = {'alsa-driver':
                      {'etch':
                           {'i386' :JobStatus.BUILD_FAILED,
                            'amd64':JobStatus.BUILD_OK},
                       'gutsy':
                           {'i386' :JobStatus.BUILD_OK,
                            'amd64':JobStatus.BUILD_OK}},
                  'alsa-firmware':
                      {'etch':
                           {'i386' :JobStatus.BUILD_OK,
                            'amd64':JobStatus.DEPWAIT},
                       'gutsy':
                           {'i386' :JobStatus.BUILD_OK,
                            'amd64':JobStatus.DEPWAIT}},
                  }

        # We must have one job for every dist/arch
        self.assertEqual(len(Job.select()), 8)

        # Check the first scheduling pass and set the status for the next one
        for b in Backport().select():

            # Target versions must be bleeding and progress zero
            self.assertEqual(b.target, '%s~%s1' % (b.bleeding, b.dist))
            self.assertEqual(b.progress,0)
            p = Package(b.pkg, b.target)

            # There must be one job for every arch in WAIT status
            for arch in Backporter().archs:
                jobs = Job.select(package_id=p.id, dist=b.dist, arch=arch)
                self.assertEqual(len(jobs),1)
                self.assertEqual(jobs[0].status, JobStatus.WAIT)
                jobs[0].status = status[b.pkg][b.dist][arch]
                jobs[0].update()

        Backporter().schedule()
        self.assertEqual(Backport('alsa-driver','etch').progress,1)
        self.assertEqual(Backport('alsa-driver','etch').archs,['amd64'])
        self.assertEqual(Backport('alsa-driver','gutsy').progress,2)
        self.assertEqual(Backport('alsa-firmware','etch').progress,1)
        self.assertEqual(Backport('alsa-firmware','etch').archs,['i386'])
        self.assertEqual(Backport('alsa-firmware','gutsy').archs,['i386'])

        # We should have two more jobs (for the DEPWAITs)
        self.assertEqual(len(Job.select()), 8 + 2)

        # Nothing happens
        Backporter().schedule()
        self.assertEqual(len(Job.select()), 8 + 2)

        # Let's add a backport to solve the DEPWAIT
        self.backports = (('freecycle',     'etch',  BackportPolicy.Smart.Value),
                          ('freecycle',     'gutsy', BackportPolicy.Smart.Value))

        for backport in self.backports:
            Backporter().add(backport[0], backport[1])
            Backporter().set(backport[0], backport[1], 'policy', backport[2])

        # New pass
        Backporter().update()
        Backporter().schedule()

        # We should have 4 brand new jobs
        self.assertEqual(len(Job.select()), 8 + 2 + 4)

        # Let's say they are all succesful..
        for dist in ['etch', 'gutsy']:
            b = Backport('freecycle',dist)
            p = Package(b.pkg, b.target)

            for arch in Backporter().archs:
                j = Job.select(package_id=p.id, dist=b.dist, arch=arch)[0]
                j.status = JobStatus.BUILD_OK
                j.update()

        # This will re-trigger the DEPWAITs
        Backporter().schedule()

        # We should have again 2 jobs for the DEPWAITs
        self.assertEqual(len(Job.select()), 8 + 2 + 4 + 2)

        # Now let's force alsa-firmware/etch/i386 re-schedule
        Backporter().set('alsa-driver', 'etch', 'policy', BackportPolicy.Always.Value)
        Backporter().schedule()
        self.assertEqual(len(Job.select()), 8 + 2 + 4 + 2 + 1)

if __name__ == '__main__':
    Database(path=':memory:')
    unittest.main()

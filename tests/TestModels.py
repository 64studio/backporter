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
from backporter.Models          import *
from backporter.Database        import Database
from backporter.BackporterError import BackporterError

class TestPackage(unittest.TestCase):

    def setUp(self):
	Database().clean()
        self.p = Package()
        self.p.name  = 'libgig'
        self.p.version = '0.1-1'

    def test_init(self):
        self.assert_(type(self.p) is Package)
        def raiseme(id):
            Package(id=id)
        self.assertRaises(BackporterError, raiseme, 100)
        def raiseme(name, version):
            Package(name=name, version=version)
        self.assertRaises(BackporterError, raiseme, 'foo', '24000')

    def test_insert(self):
        self.p.insert()
        p = Package('libgig','0.1-1')
        self.assertEqual(self.p.name, p.name)
        self.assertEqual(self.p.version, p.version)

    def test_select(self):
        self.p.insert()
        self.assertEqual(len(Package().select()), 1)

    def test_delete(self):
        self.p.insert()
        for p in Package().select():
            p.delete()
        self.assertEqual(len(Package().select()), 0)

class TestJob(unittest.TestCase):

    def setUp(self):
	Database().clean()
        self.j = Job()
        self.j.package_id  = 1
        self.j.arch  = 'amd64'
        self.j.dist  = 'etch'

    def test_init(self):
        self.assert_(type(self.j) is Job)
        def raiseme(id):
            Job(id)
        self.assertRaises(BackporterError, raiseme, 1)

    def test_insert(self):
        self.j.dist  = None
        self.assertRaises(AssertionError, self.j.insert)
        self.j.dist  = 'i386'
        self.j.insert()
        j = Job(1)
        self.assertEqual(self.j.package_id, j.package_id)
        self.assertEqual(self.j.arch, j.arch)

    def test_select(self):

        packages = ((1, 'alsa-driver',   '1.0.14-2'),
                    (2, 'ams',           '1.8.8-2'),
                    (3, 'freecycle',     '0.6alpha-2'))


        for package in packages:
            p = Package()
            (p.id, p.name, p.version) = package
            p.insert()
            j = Job()
            (j.package_id, j.dist, j.arch) = (p.id, 'etch', 'amd64')
            j.insert()
            (j.package_id, j.dist, j.arch) = (p.id, 'etch', 'i386')
            j.insert()

        self.assertEqual(len(Job().select()), 6)
        self.assertEqual(len(Job().select(package_id=1,dist='etch',arch='i386')), 1)

    def test_delete(self):
        self.j.insert()
        for j in Job().select():
            j.delete()
        self.assertEqual(len(Job().select()), 0)

class TestBackport(unittest.TestCase):

    def setUp(self):
	Database().clean()
        self.b = Backport()
        self.b.pkg  = 'libgig'
        self.b.dist = 'etch'

    def test_init(self):
        self.assert_(type(self.b) is Backport)
        def raiseme(pkg, dist):
            Backport(pkg=pkg, dist=dist)
        self.assertRaises(BackporterError, raiseme, 'libgig','etch')

    def test_insert(self):
        self.b.insert()
        b = Backport('libgig','etch')
        self.assertEqual(self.b.pkg, b.pkg)
        self.assertEqual(self.b.dist, b.dist)
        self.assertRaises(sqlite.IntegrityError,b.insert)

    def test_update(self):
        self.b.insert()
        self.b.origin = 'sid'
        self.b.archs.append('i386')
        self.b.progress = -1
        self.b.update()
        b = Backport('libgig','etch')
        self.assertEqual(b.origin, 'sid')
        self.assertEqual(b.progress, -1)
        self.assertEqual(b.archs, ['i386'])

    def test_select(self):
        self.b.insert()
        self.assertEqual(len(Backport().select()), 1)
        b = Backport()
        b.pkg  = 'liblscp'
        b.dist = 'etch'
        archs = RebuilddConfig().get('build', 'archs').split()
        b.progress = len(archs) - 1
        b.insert()
        self.assertEqual(len(Backport().select()), 2)
        self.assertEqual(len(Backport().select(progress='partial')), 1)
        self.assertEqual(len(Backport().select(progress='null')), 1)
        b.pkg  = 'qtractor'
        b.dist = 'gutsy'
        b.insert()
        b.pkg  = 'libgig'
        b.dist = 'gutsy'
        b.insert()
        self.assertEqual([b.pkg for b in Backport().select(orderBy='pkg')], ['libgig','libgig','liblscp','qtractor'])
        self.assertNotEqual([b.pkg for b in Backport().select()], ['libgig','libgig','liblscp','qtractor'])

    def test_join(self):
        packages = ((0, 'aeolus','0.6.6+2-4'),
                    (1, 'alsa-driver','1.0.14-2'),
                    (2, 'alsa-firmware','1.0.15-1'),
                    (3, 'ams','1.8.8~rc2-2'),
                    (4, 'freecycle','0.6alpha-2'),
                    (5, 'fst','1.9-3'))

        for package in packages:
            p = Package()
            (p.id, p.name, p.version) = package
            p.insert()

    def test_delete(self):
        self.b.insert()
        for b in Backport().select():
            b.delete()
        self.assertEqual(len(Backport().select()), 0)

    def test_jobs(self):

        RebuilddConfig().set('build', 'archs', 'i386 amd64')
        archs = RebuilddConfig().get('build', 'archs').split()

        backports = (('alsa-driver',   'etch',  '1.0.14-2',    2), # BUILD_OK on etch and DEPWAIT on gutsy
                     ('alsa-driver',   'gutsy', '1.0.14-2',    0),
                     ('alsa-firmware', 'etch',  '1.0.15-1',   -1), # Just added backports, not yet scheduled..
                     ('alsa-firmware', 'gutsy', '1.0.15-1',   -1),
                     ('ams',           'etch',  '1.8.8-2',     1), # FAILS on etch/amd64 BUILD_OK on gutsy
                     ('ams',           'gutsy', '1.8.8-2',     2),
                     ('freecycle',     'etch',  '0.6alpha-2',  1)) # Only etch, DEPWAIT on i386

        packages = ((1, 'alsa-driver',   '1.0.14-2'),
                    (2, 'ams',           '1.8.8-2'),
                    (3, 'freecycle',     '0.6alpha-2'))

        jobs = ((1,  JobStatus.BUILD_OK,     1, 'etch', 'amd64'),
                (2,  JobStatus.BUILD_OK,     1, 'etch', 'i386'),
                (3,  JobStatus.DEPWAIT,      1, 'gutsy', 'i386'),
                (4,  JobStatus.DEPWAIT,      1, 'gutsy', 'amd64'),
                (5,  JobStatus.BUILD_OK,     2, 'etch',  'i386'),
                (6,  JobStatus.BUILD_OK,     2, 'gutsy', 'amd64'),
                (7,  JobStatus.BUILD_FAILED, 2, 'etch', 'amd64'),
                (8,  JobStatus.BUILD_OK,     2, 'gutsy', 'i386'),
                (9,  JobStatus.DEPWAIT,      3, 'etch',  'i386'),
                (10, JobStatus.BUILD_OK,     3, 'etch',  'amd64'))

        for package in packages:
            p = Package()
            (p.id, p.name, p.version) = package
            p.insert()

        for job in jobs:
            j = Job()
            (j.id, j.status, j.package_id, j.dist, j.arch) = job
            j.insert()

        for backport in backports :
            b = Backport()
            (b.pkg, b.dist, b.target, b.progress) = backport
            b.insert()

        self.assertEqual(len(Backport().jobs()), 10)
        self.assertEqual(len(Backport().jobs(progress='complete')), 4)
        self.assertEqual(len(Backport().jobs(progress='partial')), 6)
        self.assertEqual(len(Backport().jobs(progress='partial', status=JobStatus.DEPWAIT)), 3)
        self.assertEqual(
            [b.pkg for b in Backport().jobs(progress='partial', status=JobStatus.DEPWAIT, orderBy='backport.pkg')],
            ['alsa-driver','alsa-driver','freecycle'])
        self.assertEqual(
            [(b.pkg, b.dist, b.job.arch) for b in Backport().jobs(progress='partial',
                                                                  status=JobStatus.DEPWAIT,
                                                                  orderBy='backport.pkg, backport.dist, job.arch')],
            [('alsa-driver','gutsy','amd64'),
             ('alsa-driver','gutsy','i386'),
             ('freecycle',  'etch' ,'i386')])

if __name__ == '__main__':
    Database(path=':memory:')
    unittest.main()

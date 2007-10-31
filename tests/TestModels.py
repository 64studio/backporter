#!/usr/bin/env python2.5
import sys  
  
sys.path.insert(0, "..")  
sys.path.insert(0, ".")  

import unittest
import types
import os

from pysqlite2                  import dbapi2 as sqlite
from BackporterTestSetup import backporter_global_test_setup
from rebuildd.RebuilddConfig    import RebuilddConfig
from backporter.Models          import *
from backporter.Database        import Database
from backporter.BackporterError import BackporterError

class TestPackage(unittest.TestCase):

    def setUp(self):
        backporter_global_test_setup()
        self.p = Package()

    def test0_init(self):
        self.assert_(type(self.p) is Package)
        def raiseme(id):
            Package(id=id)
        self.assertRaises(BackporterError, raiseme, 1)
        def raiseme(name, version):
            Package(name=name, version=version)
        self.assertRaises(BackporterError, raiseme, 'libgig', '0.1-1')

    def test1_insert(self):
        self.p.name  = 'libgig'
        self.p.version = '0.1-1'
        self.p.insert()
        p = Package('libgig','0.1-1')
        self.assertEqual(self.p.name, p.name)
        self.assertEqual(self.p.version, p.version)

    def test2_select(self):
        self.assertEqual(len(Package().select()), 1)

    def test3_delete(self):
        for p in Package().select():
            p.delete()
        self.assertEqual(len(Package().select()), 0)

class TestJob(unittest.TestCase):

    def setUp(self):
        backporter_global_test_setup()
        self.j = Job()

    def test0_init(self):
        self.assert_(type(self.j) is Job)
        def raiseme(id):
            Job(id)
        self.assertRaises(BackporterError, raiseme, 1)

    def test1_insert(self):
        self.j.package_id  = 1
        self.j.arch  = 'amd64'
        self.assertRaises(AssertionError, self.j.insert)
        self.j.dist  = 'etch'
        self.j.insert()
        j = Job(1)
        self.assertEqual(self.j.package_id, j.package_id)
        self.assertEqual(self.j.arch, j.arch)

    def test2_select(self):
        self.assertEqual(len(Job().select()), 1)

    def test3_delete(self):
        for j in Job().select():
            j.delete()
        self.assertEqual(len(Job().select()), 0)

class TestBackport(unittest.TestCase):

    def setUp(self):
        backporter_global_test_setup()
        self.b = Backport()

    def test0_init(self):
        self.assert_(type(self.b) is Backport)
        def raiseme(pkg, dist):
            Backport(pkg=pkg, dist=dist)
        self.assertRaises(BackporterError, raiseme, 'libgig','etch')

    def test1_insert(self):
        self.b.pkg  = 'libgig'
        self.b.dist = 'etch'
        self.b.insert()
        b = Backport('libgig','etch')
        self.assertEqual(self.b.pkg, b.pkg)
        self.assertEqual(self.b.dist, b.dist)
        self.assertRaises(sqlite.IntegrityError,b.insert)

    def test2_update(self):
        self.b = Backport('libgig','etch')
        self.b.origin = 'sid'
        self.b.archs.append('i386')
        self.b.progress = -1
        self.b.update()
        b = Backport('libgig','etch')
        self.assertEqual(b.origin, 'sid')
        self.assertEqual(b.progress, -1)
        self.assertEqual(b.archs, ['i386'])

    def test3_select(self):
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

    def test4_delete(self):
        for b in Backport().select():
            b.delete()
        self.assertEqual(len(Backport().select()), 0)

if __name__ == '__main__':
    unittest.main()

import random
import unittest
import os
from pysqlite2.dbapi2 import IntegrityError

#from data import *
from rebuildd.RebuilddConfig import RebuilddConfig
from backporter.Models      import *
from backporter.Database    import Database
from backporter.BackporterError import BackporterError

#from backporter.Backporterd import Backporterd

class ModelsTestCase(unittest.TestCase):
    
    def test_models(self):
        cnx = Database().get_cnx()
        cursor = cnx.cursor()
        cursor.execute('DELETE FROM backport')
        cnx.commit()

        # New
        b = Backport()
        def raiseme(pkg, dist):
            Backport(pkg=pkg, dist=dist)
        self.assertRaises(BackporterError, raiseme, 'libgig','etch')

        # Insert
        b.pkg  = 'libgig'
        b.dist = 'etch'
        b.insert()
        b2 = Backport('libgig','etch')
        self.assertEqual(b.pkg, b2.pkg)
        self.assertEqual(b.dist, b2.dist)
        self.assertRaises(IntegrityError,b2.insert)

        # Update
        b.origin = 'sid'
        b.archs.append('i386')
        b.progress = -1
        b.update()
        b2 = Backport('libgig','etch')
        self.assertEqual(b2.origin, 'sid')
        self.assertEqual(b2.progress, -1)
        self.assertEqual(b2.archs, ['i386'])

        # Select
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

        # Delete
        for b in Backport().select():
            b.delete()
        self.assertEqual(len(Backport().select()), 0)

if __name__ == '__main__':
    unittest.main()

import random
import unittest
import os

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
        self.b = Backport()
        def raiseme(pkg, dist):
            Backport(pkg=pkg, dist=dist)
        self.assertRaises(BackporterError, raiseme, 'libgig','etch')

        # Insert
        self.b.pkg  = 'libgig'
        self.b.dist = 'etch'
        self.b.insert()
        self.b2 = Backport('libgig','etch')
        self.assertEqual(self.b.pkg, self.b2.pkg)
        self.assertEqual(self.b.dist, self.b2.dist)

        # Update
        self.b.origin = 'sid'
        self.b.archs.append('i386')
        self.b.update()
        self.b2 = Backport('libgig','etch')
        self.assertEqual(self.b2.origin, 'sid')
        self.assertEqual(self.b2.archs, ['i386'])

        # Select
        self.assertEqual(len(Backport().select()), 1)
        self.b = Backport()
        self.b.pkg  = 'liblscp'
        self.b.dist = 'etch'
        self.b.insert()
        self.assertEqual(len(Backport().select()), 2)

        # Delete
        for b in Backport().select():
            b.delete()
        self.assertEqual(len(Backport().select()), 0)

if __name__ == '__main__':
    unittest.main()

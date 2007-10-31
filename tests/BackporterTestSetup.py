import os

from rebuildd.RebuilddConfig import RebuilddConfig
from backporter.Database     import Database

def backporter_global_test_setup():
        RebuilddConfig().set('build', 'database_uri', 'sqlite:///tmp/backporter-tests.db')
	Database()
        try:
            os.unlink("/tmp/backporter-tests.db")
        except OSError:
            pass
        try:
            Database()
        except:
             pass

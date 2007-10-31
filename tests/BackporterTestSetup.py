import os

from rebuildd.RebuilddConfig import RebuilddConfig
from backporter.Database     import Database

def backporter_global_test_setup():
	# Drops all tables
	Database().clean()
#	pass

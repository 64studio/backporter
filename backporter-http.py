#!/usr/bin/env python2.5

import web
from backporter.BackporterWeb    import BackporterWeb
from backporter.BackporterConfig import BackporterConfig

import sys, os

try:
    os.chdir(BackporterConfig().get('http', 'templates'))
except Exception, error:
    print "E: cannot chdir to templates: %s" % error
    sys.exit(1)

BackporterWeb().start()

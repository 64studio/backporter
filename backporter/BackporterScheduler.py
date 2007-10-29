# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import re
import telnetlib
import socket
import datetime

import warnings
warnings.simplefilter('ignore', FutureWarning)

from backporter.BackporterConfig import BackporterConfig
from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Models   import *

#from rebuildd.JobStatus          import JobStatus

__all__ = ['BackporterScheduler']

class BackporterScheduler(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
        if cls._instance is None:  
            cls._instance = object.__new__(cls)  
            cls._instance.init(*args, **kwargs)
        return cls._instance  

    def init(self):

        from sqlobject import sqlhub, connectionForURI
        dburi = 'sqlite://' + os.path.join(BackporterConfig().get('config', 'database'), 'rebuildd.db')
        sqlhub.processConnection = connectionForURI(dburi)

        self.archs = BackporterConfig().get('config', 'archs').split()
        self.priority = '1' # Default job priority

    # Schedule build jobs for the packages that need to be backported
    def schedule(self):

        # Iter over all backports
        for b in Backport.select():

            # Skip freezed backports
            if b.status == BackportStatus.Freezed.Value:
                continue

            # Schedule only on selected dists
            if b.options and b.options.has_key("dist"):
                dists = [Dist(b.options['dist'])]
            else:
                dists = Dist.select(DistType.Released.Value)

            # Check every dist
            for d in dists:
                try:
                    # Get the source in the relased dist
                    sr = Source(b.package, d.name)
                except Exception, e:
                    # No source available
                    sr = Source()
                    sr.package = b.package
                    sr.dist    = d.name
                    sr.version = '0'

                sb = Source(b.package, b.bleeding())
                if b.package == 'freecycle':
                    import pdb
                    pdb.set_trace()
                # If the bleeding edge version is greater than the official, then try
                # to schedule a new job
                if Source.compare(sb, sr) >= 1:
                    version = '%s~%s1' % (sb.version, d.name)
                    try:
                        # Get the package element
                        p = Package(b.package,version)
                    except Exception, e:
                        version_bpo = '%s~bpo.1' % (sb.version)
                        try:
                            # Get the package element
                            p = Package(b.package,version_bpo)
                        except Exception, e:
                            # No such package available, insert a new object
                            p = Package()
                            p.name    = b.package
                            p.version = version
                            p.insert()
                            p = Package(b.package,version) # This query could probably be avoided

                    # Schedule only on selected dists
                    if b.options and b.options.has_key("dist"):
                        archs = [b.options['arch']]
                    else:
                        archs = self.archs

                    # Iter for each arch
                    for arch in archs:
                        jobs = Job.select(package_id=p.id, dist=d.name, arch=arch)
                        if len(jobs) >= 1:
                            continue # Already scheduled

                        # Add a new job
                        j = Job()
                        j.status = 100
                        j.package_id = p.id
                        j.dist = d.name
                        j.arch = arch
                        j.insert()

                        # TODO: this is now useless, should be deleted
                        b.version = version
                        b.stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
                        b.update()

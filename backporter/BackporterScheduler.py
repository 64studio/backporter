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
#from rebuildd.Job                import Job
#from rebuildd.Package import rebuildd.Package

from pysqlite2 import dbapi2 as sqlite

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

        path = os.path.join(BackporterConfig().get('config', 'database'),'rebuildd.db')
        cnx = sqlite.connect(path, check_same_thread=False)
        cursor = cnx.cursor()

        from backporter.BackporterScheduler import BackporterScheduler
        for b in Backport.select():

            if b.status == BackportStatus.Freezed.Value:
                continue

            for d in Dist.select(DistType.Released.Value):

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

                # If the bleeding edge version is greater than the official, then try
                # to schedule a new job
                if Source.compare(sb, sr) >= 1:
                    version = '%s~%s1' % (sb.version, d.name)
                    try:
                        # Get the package element
                        p = Package(b.package,version)
                    except Exception, e:
                        # No such package available, insert it
                        p = Package()
                        p.name    = b.package
                        p.version = version
                        p.insert()
                        p = Package(b.package,version)

                    # Iter for each arch
                    for arch in self.archs:
                        jobs = Job.select(package_id=p.id, arch=arch)
                        if len(jobs) >= 1:
                            continue # Already scheduled

                        # Add a new job
                        j = Job()
                        j.status = 100
                        j.package_id = p.id
                        j.dist = d.name
                        j.arch = arch
                        j.insert()

                        b.version = version
                        b.stamp = datetime.datetime.now()
                        b.update()

    def job_status(self, package, version, dist, arch):

        pkgs = Package.selectBy(name=package, version=version)
        if pkgs.count():
            # If several packages exists, just take the first
            pkg = pkgs[0]
        else:
            # Maybe we found no packages, so create a brand new one!
            pkg = Package(name=package, version=version, priority=self.priority)

        jobs = Job.selectBy(package=pkg.id, dist=dist, arch=arch)
        if jobs.count():
            return (pkg.id, jobs[0].status)
        else:
            return (pkg.id, JobStatus.UNKNOWN)

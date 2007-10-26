# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import re
import telnetlib
import socket
import warnings
warnings.simplefilter('ignore', FutureWarning)

from backporter.BackporterConfig import BackporterConfig
from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Models   import *

from rebuildd.RebuilddConfig import RebuilddConfig
from rebuildd.Job            import Job, JobStatus
from rebuildd.Package        import Package

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

        from backporter.BackporterScheduler import BackporterScheduler
        for b in Backport.select():

            if b.status == BackportStatus.Freezed.Value:
                continue

            for d in Dist.select(DistType.Released.Value):

                sr = Source(b.package, d.name)
                sb = Source(b.package, b.bleeding())

                if Source.compare(sb, sr) >= 1:

                    version = '%s~%s1' % (sb.version, d.name)
                    
                    for arch in self.archs:

                        (id, status) = self.job_status(b.package, version, d.name, arch)

                        if status != JobStatus.UNKNOWN:
                            continue # Already scheduled

                        # Add a new job
                        job = Job(package=id, dist=d.name, arch=arch)
                        job.status = JobStatus.WAIT
                        job.arch = arch
                        job.mailto = None


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

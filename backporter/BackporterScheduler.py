# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import re
import apt_pkg
import telnetlib
import socket

from backporter.BackporterConfig import BackporterConfig
from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Models   import *

apt_pkg.InitConfig()
apt_pkg.InitSystem()

__all__ = ['BackporterScheduler']

class Scheduler(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
        if cls._instance is None:  
            cls._instance = object.__new__(cls)  
            cls._instance.init(*args, **kwargs)
        return cls._instance  

    def init(self):

        # Try to connect to backporterd
        self.host    = '0.0.0.0'
        self.port    = '9999'
        self.timeout = 5
        self.prompt  = 'rebuildd@localhost->'
        try:
            self.cnx   = telnetlib.Telnet(self.host, self.port)
            self.cnx.read_until(self.prompt)
            Logger().debug("Connected to backported")
        except socket.error, msg:
            self.cnx   = None
            Logger().debug("Could not connect to backported")


    def job_status(self, package, version, dist, arch):
        if not self.cnx:
            Logger().debug("Not connected to backported")
            return
        print(str('job status %s %s %s %s' % \
                           (package, version, dist, arch)))
        self.cnx.write(str('job status %s %s %s %s\n' % \
                           (package, version, dist, arch)))

        (i,m,ans) = self.cnx.expect(['None',self.prompt])
#        self.cnx.read_very_eager()
        print ans
        if i == 1:
            return None
        return ans[ans.find('status'):].split(" ")[1]

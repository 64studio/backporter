# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os

from backporter.Config   import Config
from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Models   import *


__all__ = ['Backporter']

class Backporter(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
        if cls._instance is None:  
           cls._instance = object.__new__(cls)  
           cls._instance.init(*args, **kwargs)
        return cls._instance  

    def init(self):
        return

    def suite_add(self, name, type, url, comp):
        s = Suite()
        s.name = name
        s.type = SuiteType.Bleeding.Value # FIX
        s.url  = url
        s.comp = comp
        s.insert()

    def suite_remove(self, name):
        s = Suite()
        s.name = name
        s.delete()

    def suite_update(self, name, type, url, comp):
        s = Suite()
        s.name = name
        s.type = SuiteType.Bleeding.Value # FIX
        s.url  = url
        s.comp = comp
        s.update()

    def backport_add(self, package, status, options):
        b = Backport()
        b.package = package
        b.type    = status
        b.options = options
        b.insert()

    def backport_remove(self, package):
        b = Backport()
        b.package = package
        b.delete()

    def backport_update(self, package, status, options):
        b = Backport()
        b.package = package
        b.status  = status
        b.options = options
        b.update()

    def source_add(self, package, suite, version):
        s = Source()
        s.package = package
        s.suite   = suite
        s.version = version
        s.insert()

    def source_remove(self, package, suite):
        s = Source()
        s.package = package
        s.suite = suite
        s.delete()

    def source_update(self, package, suite, version):
        s = Source()
        s.package = package
        s.suite  = suite
        s.version = version
        s.update()

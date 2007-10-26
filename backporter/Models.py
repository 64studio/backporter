# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import sys
import re
import string

from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Enum     import Enum
from apt_pkg             import VersionCompare

__all__ = ['Dist', 'DistType', 'Backport', 'BackportStatus','Source']

DistType = Enum('Dummy', 'Released', 'Bleeding')

class Dist(object):

    def __init__(self, name=None):
        self.cnx = Database().get_cnx()
        if name:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT type,url,comp FROM dist WHERE name='%s'" % (name))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Dist %s does not exist.' % name
            self.name = name
            self.type = row[0]
            self.url  = row[1]
            self.comp = row[2]
        else:
            self.name = None
            self.type = None
            self.url = None
            self.comp = None

    def delete(self):
        assert self.name, 'Cannot deleting non-existent dist'
        self.name = self.name.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Deleting dist '%s'" % self.name)
        cursor.execute("DELETE FROM dist WHERE name='%s'" % self.name)
        self.cnx.commit()

        for b in Backport.select():
            source = Source()
            s.package  = b.package
            s.dist     = self.name
            s.delete()

    def insert(self):
        assert self.name, 'Cannot create dist with no name'
        self.name = self.name.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Creating new dist '%s'" % self.name)
        cursor.execute("INSERT INTO dist VALUES ('%s',%d,'%s','%s')" % (self.name, self.type, self.url, self.comp))

        for b in Backport.select():
            s = Source()
            s.package  = b.package
            s.dist     = self.name
            s.version  = '0'
            s.insert()

        self.cnx.commit()

    def update(self):
        assert self.name, 'Cannot update non-existent dist'
        self.name = self.name.strip()
        cursor = self.cnx.cursor()
        Logger().debug('Updating dist "%s"' % self.name)
        cursor.execute("UPDATE dist SET name='%s',type=%d, url='%s', comp='%s' WHERE name='%s'" % \
                           (self.name, self.type, self.url, self.comp, self.name))

        self.cnx.commit()

    def select(cls, type=None):
        cursor = Database().get_cnx().cursor()
        if not type:
            cursor.execute("SELECT name,type,url,comp FROM dist")
        else:
            cursor.execute("SELECT name,type,url,comp FROM dist WHERE type=%d" % type)
        dists = []
        for name, type, url, comp in cursor:
            s = cls()
            s.name = name
            s.type = type
            s.url  = url
            s.comp = comp
            dists.append(s)
        return dists
    select = classmethod(select)

BackportStatus = Enum('Dummy', 'Freezed', 'AutoUpdate')

class Backport(object):

    def __init__(self, package=None):
        self.cnx = Database().get_cnx()
        if package:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT status, options FROM backport WHERE package='%s'" % (package))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Backport %s does not exist.' % name
            self.package = package
            self.status  = row[0]
            self.options  = row[1]
        else:
            self.package = None
            self.status  = True
            self.options  = None

    def delete(self):
        assert self.package, 'Cannot deleting non-existent backport'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Deleting backport '%s'" % self.package)
        cursor.execute("DELETE FROM backport WHERE package='%s'" % self.package)
        self.cnx.commit()

        for d in Dist.select():
            s = Source()
            s.package = self.package
            s.dist   = d.name
            s.delete()

    def insert(self):
        assert self.package, 'Cannot create backport with no package'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Creating new backport '%s'" % self.package)
        cursor.execute("INSERT INTO backport VALUES ('%s',%d, '%s')" % (self.package, self.status, self.options))

        for d in Dist.select():
            s = Source()
            s.package = self.package
            s.dist   = d.name
            s.version = '0'
            s.insert()

        self.cnx.commit()

    def update(self):
        assert self.package, 'Cannot update non-existent backport'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug('Updating backport "%s"' % self.package)
        cursor.execute("UPDATE backport SET package='%s',status=%d, options='%s' WHERE package='%s'" % \
                           (self.package, self.status, self.options, self.package))

        self.cnx.commit()

    def select(cls, status=None):
        cursor = Database().get_cnx().cursor()
        if not status:
            cursor.execute("SELECT package,status,options FROM backport")
        else:
            cursor.execute("SELECT package,status,options FROM backport WHERE status=%d" % status)
        backports = []
        for package, status, options in cursor:
            b = cls()
            b.package = package
            b.status  = status
            b.options = options
            backports.append(b)
        return backports
    select = classmethod(select)

    # Return the bleeding edge dist for this backport
    def bleeding(self):

        bleeding = None
        for d in Dist().select(DistType.Bleeding.Value):
            s = Source(self.package, d.name)
            if bleeding:
                b = Source(self.package, bleeding)
                if Source.compare(a, b) <= -1:
                    bleeding = d.name
            else:
                bleeding = d.name
        return bleeding

class Source(object):

    def __init__(self, package=None, dist=None):
        self.cnx = Database().get_cnx()
        if package and dist:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT version FROM source WHERE package='%s' and dist='%s'" % (package, dist))
            row = cursor.fetchone()
            if not row:
                raise Exception, 'Source %s does not exist.' % name
            self.package = package
            self.dist   = dist
            self.version = row[0]
        else:
            self.package = None
            self.dist   = None
            self.version = None

    def delete(self):
        assert self.package and self.dist, 'Cannot deleting non-existent source'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Deleting source '%s'" % self.package)
        cursor.execute("DELETE FROM source WHERE package='%s' and dist='%s'" % (self.package, self.dist))
        self.cnx.commit()

    def insert(self):
        assert self.package and self.dist, 'Cannot create source with no package'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Creating new source '%s','%s'" % (self.package, self.dist))
        cursor.execute("INSERT INTO source VALUES ('%s','%s', '%s')" % (self.package, self.dist, self.version))

        self.cnx.commit()

    def update(self):
        assert self.package and self.dist, 'Cannot update non-existent source'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug('Updating source "%s","%s"' % (self.package, self.dist))
        cursor.execute("UPDATE source SET version='%s' WHERE package='%s' and dist='%s'" % \
                           (self.version, self.package,self.dist))

        self.cnx.commit()

    def select(cls, dist=None):
        cursor = Database().get_cnx().cursor()
        if not dist:
            cursor.execute("SELECT package,dist,version FROM source")
        else:
            cursor.execute("SELECT package,dist,version FROM source WHERE dist='%s'" % dist)
        sources = []
        for package, dist, version in cursor:
            b = cls()
            b.package  = package
            b.dist    = dist
            b.version  = version
            sources.append(b)
        return sources
    select = classmethod(select)

    @staticmethod
    def compare(a, b):
        return VersionCompare(a.version, b.version)

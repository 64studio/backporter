# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Enum     import Enum

__all__ = ['Suite', 'SuiteType', 'Backport', 'BackportStatus','Source']

SuiteType = Enum('Dummy', 'Released', 'Bleeding')

class Suite(object):

    def __init__(self, name=None):
        self.cnx = Database().get_cnx()
        if name:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT type,url,comp FROM suite WHERE name='%s'" % (name))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Suite %s does not exist.' % name
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
        assert self.name, 'Cannot deleting non-existent suite'
        self.name = self.name.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Deleting suite '%s'" % self.name)
        cursor.execute("DELETE FROM suite WHERE name='%s'" % self.name)
        self.cnx.commit()

        for b in Backport.select():
            source = Source()
            source.package = b.package
            source.suite   = self.name
            source.version   = None
            source.delete()

    def insert(self):
        assert self.name, 'Cannot create suite with no name'
        self.name = self.name.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Creating new suite '%s'" % self.name)
        cursor.execute("INSERT INTO suite VALUES ('%s',%d,'%s','%s')" % (self.name, 0, self.url, self.comp))

        for b in Backport.select():
            source = Source()
            source.package = b.package
            source.suite   = self.name
            source.version   = None
            source.insert()

        self.cnx.commit()

    def update(self):
        assert self.name, 'Cannot update non-existent suite'
        self.name = self.name.strip()
        cursor = self.cnx.cursor()
        Logger().debug('Updating suite "%s"' % self.name)
        cursor.execute("UPDATE suite SET name='%s',type=%d, url='%s', comp='%s' WHERE name='%s'" % \
                           (self.name, self.type, self.url, self.comp, self.name))

        self.cnx.commit()

    def select(cls, type=None):
        cursor = Database().get_cnx().cursor()
        if not type:
            cursor.execute("SELECT name,type,url,comp FROM suite")
        else:
            cursor.execute("SELECT name,type,url,comp FROM suite WHERE type=%d" % type)
        suites = []
        for name, type, url, comp in cursor:
            s = cls()
            s.name = name
            s.type = type
            s.url  = url
            s.comp = comp
            suites.append(s)
        return suites
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

        for s in Suite.select():
            source = Source()
            source.package = self.package
            source.suite   = s.name
            source.delete()

    def insert(self):
        assert self.package, 'Cannot create backport with no package'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Creating new backport '%s'" % self.package)
        cursor.execute("INSERT INTO backport VALUES ('%s',%d, '%s')" % (self.package, self.status, self.options))

        for s in Suite.select():
            source = Source()
            source.package = self.package
            source.suite   = s.name
            source.version = None
            source.insert()

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

class Source(object):

    def __init__(self, package=None, suite=None):
        self.cnx = Database().get_cnx()
        if package and suite:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT version FROM source WHERE package='%s' and suite='%s'" % (package, suite))
            row = cursor.fetchone()
            if not row:
                raise SourceerError, 'Source %s does not exist.' % name
            self.package = package
            self.suite   = suite
            self.version = row[0]
        else:
            self.package = None
            self.suite   = None
            self.version = None

    def delete(self):
        assert self.package and self.suite, 'Cannot deleting non-existent source'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Deleting source '%s'" % self.package)
        cursor.execute("DELETE FROM source WHERE package='%s' and suite='%s'" % (self.package, self.suite))
        self.cnx.commit()

    def insert(self):
        assert self.package and self.suite, 'Cannot create source with no package'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug("Creating new source '%s','%s'" % (self.package, self.suite))
        cursor.execute("INSERT INTO source VALUES ('%s','%s', '%s')" % (self.package, self.suite, self.version))

        self.cnx.commit()

    def update(self):
        assert self.package and self.suite, 'Cannot update non-existent source'
        self.package = self.package.strip()
        cursor = self.cnx.cursor()
        Logger().debug('Updating source "%s","%s"' % (self.package, self.suite))
        cursor.execute("UPDATE source SET version='%s' WHERE package='%s' and suite='%s'" % \
                           (self.version, self.package,self.suite))

        self.cnx.commit()

    def select(cls, suite=None):
        cursor = Database().get_cnx().cursor()
        if not suite:
            cursor.execute("SELECT package,suite,version FROM source")
        else:
            cursor.execute("SELECT package,suite,version FROM source WHERE suite='%s'" % suite)
        sources = []
        for package, suite, version in cursor:
            b = cls()
            b.package  = package
            b.suite    = suite
            b.version  = version
            sources.append(b)
        return sources
    select = classmethod(select)


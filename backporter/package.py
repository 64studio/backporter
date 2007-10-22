# -*- coding: utf-8 -*-
# 
# Copyright (C) 2007 Free Ekanayaka

import re
import sys
import time

from backporter.utils import *
from backporter.suite import *

__all__ = ['Package', 'PackageStatus', 'Version']

# HACK: Use Dummy as unicode doesn't like to print 0
PackageStatus = Enum('Dummy', 'Todo')

#PACKAGE_STATUS_OK      = 6
#PACKAGE_STATUS_TODO    = 7
#PACKAGE_STATUS_DEPWAIT = 8
#PACKAGE_STATUS_FAILED  = 9
#PACKAGE_STATUS_WORKING = 10

class Package(object):

    def __init__(self, ws, name=None, db=None):
        self.ws = ws
        if name:
            if not db:
                db = self.ws.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT status FROM package WHERE name='%s'" % name)
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Package %s does not exist.' % name
            self.status = row[0]
#            self.version = {}
#            for s in Suite.select(self):
#                self.version[suite] = self.get_version(suite)
            self.name = name
            self.status = PackageStatus.Todo
        else:
            self.name = None
            self.version = {}

    exists = property(fget=lambda self: self.name is not None)

    def delete(self, db=None):
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Deleting package %s' % self.name)
        cursor.execute("DELETE FROM package WHERE name='%s'" % self.name)

        self.name  = None

        if handle_ta:
            db.commit()

    def insert(self, db=None):
        assert self.name, 'Cannot create package with no name'
        self.name = self.name.strip()
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug("Creating new package '%s'" % self.name)
        cursor.execute("INSERT INTO package VALUES ('%s',%d)" % (self.name,PackageStatus.Todo.Value))

        if handle_ta:
            db.commit()
        for s in Suite.select(self.ws):
            v = Version(self.ws)
            v.package = self.name
            v.suite   = s.name
            v.value   = None
            v.insert()

    def update(self, db=None):
        assert self.name, 'Cannot update package with no name'
        self.name = self.name.strip()
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Updating package "%s"' % self.name)
        cursor.execute("UPDATE package SET name='%s',status=%d WHERE name='%s'" %
                       (self.name, self.status, self.name))
 
        if handle_ta:
            db.commit()

    def select(cls, ws, db=None):
        if not db:
            db = ws.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT name, status FROM package")
        packages = []
        for name, status in cursor:
            package = cls(ws)
            package.name = name
            package.status = status
#            for s in Suite.select(ws):
#                package.version[s.name] = package.get_version(s)
            packages.append(package)
        return packages
    select = classmethod(select)

#    def get_version(self, suite, db=None):
#        if not db:
#            db = self.ws.get_db_cnx()
#        cursor = db.cursor()
#        cursor.execute("SELECT version FROM version WHERE package='%s' and suite='%s'" % (self.name, suite.name))
#        return cursor.fetchone()

class Version(object):

    def __init__(self, ws, package=None, suite=None, db=None):
        self.ws = ws
        if package and suite:
            if not db:
                db = self.ws.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT version FROM version WHERE package='%s' suite='%s'" % (package,suite))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Version %s does not exist.' % package
            self.package = package
            self.suite = suite
            self.value = row[0]
        else:
            self.package = None
            self.suite = None
            self.value = None

    exists = property(fget=lambda self: self.value is not None)

    def delete(self, db=None):
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Deleting version %s %' % (self.package, self.suite))
        cursor.execute("DELETE FROM version WHERE package='%s'" % (self.name,self.suite))

        self.name  = None

        if handle_ta:
            db.commit()

    def insert(self, db=None):
        assert self.package and self.suite, 'Cannot create version with no package and suite'
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug("Creating new version '%s %s %s'" % (self.package,self.suite,self.value) )
        cursor.execute("INSERT INTO version VALUES ('%s','%s','%s')" % (self.package,self.suite,self.value))

        if handle_ta:
            db.commit()

    def update(self, db=None):
        assert self.package and self.suite, 'Cannot update version with no package and suite'
        self.value = self.value.strip()
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Updating version "%s %s %s"' % (self.package,self.suite,self.value))
        cursor.execute("UPDATE version SET value='%s' WHERE package='%s' and suite='%s'" %
                       (self.package,self.suite,self.value))
 
        if handle_ta:
            db.commit()

    def select(cls, ws, db=None):
        if not db:
            db = ws.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT name, status FROM package")
        packages = []
        for name, status in cursor:
            package = cls(ws)
            package.name = name
            package.status = status
#            for s in Suite.select(ws):
#                package.version[s.name] = package.get_version(s)
            packages.append(package)
        return packages
    select = classmethod(select)

    def get_version(self, suite, db=None):
        if not db:
            db = self.ws.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT version FROM version WHERE package='%s' and suite='%s'" % (self.name, suite.name))
        return cursor.fetchone()

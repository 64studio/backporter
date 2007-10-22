# -*- coding: utf-8 -*-
# 
# Copyright (C) 2007 Free Ekanayaka

import re
import sys
import time

from backporter.utils import *
import apt_pkg,sys,re,string;

apt_pkg.InitConfig();
apt_pkg.InitSystem();

__all__ = ['Package', 'PackageStatus', 'Version', 'Suite', 'SuiteType', 'Build', 'BuildAction']


# HACK: Use Dummy as unicode doesn't like to print 0
SuiteType = Enum('Dummy', 'Released', 'Bleeding')

class Suite(object):

    def __init__(self, ws, name=None, db=None):
        self.ws = ws
        if name:
            if not db:
                db = self.ws.get_db_cnx()

            cursor = db.cursor()
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

    def delete(self, db=None):
        assert self.exists, 'Cannot deleting non-existent suite'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Deleting suite %s' % self.name)
        cursor.execute("DELETE FROM suite WHERE name=%s", (self.name,))

        self.name = self._old_name = None

        if handle_ta:
            db.commit()

    def insert(self, db=None):
        assert self.name, 'Cannot create suite with no name'
        self.name = self.name.strip()
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug("Creating new suite '%s'" % self.name)
        cursor.execute("INSERT INTO suite VALUES ('%s',%d,'%s','%s')" % (self.name, 0, self.url, self.comp))

        for p in Package.select(self.ws):
            v = Version(self.ws)
            v.package = p.name
            v.suite   = self.name
            v.value   = None
            v.insert()

            for a in self.ws.archs:
                b = Build(self.ws)
                b.package = p.name
                b.suite   = self.name
                b.arch    = a
                b.action  = BuildAction.Schedule.Value
                b.insert()

        if handle_ta:
            db.commit()

    def update(self, db=None):
        assert self.name, 'Cannot update non-existent suite'
        self.name = self.name.strip()
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Updating suite "%s"' % self.name)
        cursor.execute("UPDATE suite SET name=%s,time=%s,description=%s "
                       "WHERE name=%s",
                       (self.name, self.time, self.description,
                        self._old_name))
        if self.name != self._old_name:
            # Update tickets
            cursor.execute("UPDATE ticket SET suite=%s WHERE suite=%s",
                           (self.name, self._old_name))
            self._old_name = self.name

        if handle_ta:
            db.commit()

    def select(cls, ws, type=None, db=None):
        if not db:
            db = ws.get_db_cnx()
        cursor = db.cursor()
        if not type:
            cursor.execute("SELECT name,type,url,comp FROM suite")
        else:
            cursor.execute("SELECT name,type,url,comp FROM suite WHERE type=%d" % type)
        suites = []
        for name, type, url, comp in cursor:
            suite = cls(ws)
            suite.name = name
            suite.type = type
            suite.url  = url
            suite.comp = comp
            suites.append(suite)
        return suites
    select = classmethod(select)

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
            self.status   = row[0]
            self.name = name
            self.status = PackageStatus.Todo # FIX THIS
        else:
            self.name = None

    exists = property(fget=lambda self: self.name is not None)

    def get_bleeding(self):

        bleeding = None
        for s in Suite.select(self.ws, SuiteType.Bleeding.Value):
            v = Version(self.ws, self.name, s.name)
            if bleeding:
                b = Version(self.ws, self.name, bleeding)
                if apt_pkg.VersionCompare(b.value, v.value) <= -1:
                    bleeding = s.name
            else:
                bleeding = s.name
        return bleeding


    def delete(self, db=None):
        assert self.name, 'Cannot delete non-existing "%s"' % self.name
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Deleting package %s' % self.name)
        cursor.execute("DELETE FROM package WHERE name='%s'" % self.name)

        if handle_ta:
            db.commit()

        for s in Suite.select(self.ws):
            v = Version(self.ws)
            v.package = self.name
            v.suite   = s.name
            v.value   = None
            v.delete()

            for a in self.ws.archs:
                b = Build(self.ws)
                b.package = self.name
                b.suite   = s.name
                b.arch    = a
                b.action  = None
                b.delete()

        self.name  = None

    def insert(self, db=None):
        assert self.name, 'Cannot insert non-existing "%s"' % self.name
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

            for a in self.ws.archs:
                b = Build(self.ws)
                b.package = self.name
                b.suite   = s.name
                b.arch    = a
                b.action  = BuildAction.Schedule.Value
                b.insert()

    def update(self, db=None):
        assert self.name, 'Cannot update non-existing "%s"' % self.name
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
            packages.append(package)
        return packages
    select = classmethod(select)

class Version(object):

    def __init__(self, ws, package=None, suite=None, db=None):
        self.ws = ws
        if package and suite:
            if not db:
                db = self.ws.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT value FROM version WHERE package='%s' and suite='%s'" % (package,suite))
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
        assert self.package and self.suite, 'Cannot delete non-existing "%s %s"' % (self.package, self.suite)
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Deleting version %s %s' % (self.package, self.suite))
        cursor.execute("DELETE FROM version WHERE package='%s' and suite='%s'" % (self.package,self.suite))

        self.name  = None

        if handle_ta:
            db.commit()

    def insert(self, db=None):
        assert self.package and self.suite, 'Cannot insert non-existing "%s %s"' % (self.package, self.suite)
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        if not self.value:
            self.value = '0'
        self.ws.log.debug("Creating new version '%s %s %s'" % (self.package,self.suite,self.value) )
        cursor.execute("INSERT INTO version VALUES ('%s','%s','%s')" % (self.package,self.suite,self.value))

        if handle_ta:
            db.commit()

    def update(self, db=None):
        assert self.package and self.suite, 'Cannot update non-existing "%s %s"' % (self.package, self.suite)
        self.value = self.value.strip()
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Updating version "%s %s %s"' % (self.package,self.suite,self.value))
        cursor.execute("UPDATE version SET value='%s' WHERE package='%s' and suite='%s'" %
                       (self.value,self.package,self.suite))
 
        if handle_ta:
            db.commit()

    def select(cls, ws, db=None):
        if not db:
            db = ws.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT package, suite, value FROM version")
        versions = []
        for package, suite, value in cursor:
            version = cls(ws)
            version.package = package
            version.suite   = suite
            version.value   = value
            versions.append(version)
        return versions
    select = classmethod(select)

# HACK: Use Dummy as unicode doesn't like to print 0
BuildAction = Enum('Dummy', 'Schedule')

#PACKAGE_BUILD_SCHEDULE = 0
#PACKAGE_BUILD_SUCCESS  = 1
#PACKAGE_BUILD_FAILED   = 2
#PACKAGE_BUILD_DEPWAIT  = 3
#PACKAGE_BUILD_WORKING  = 4
#PACKAGE_BUILD_LOCK     = 5
#PACKAGE_BUILD_SKIP     = 6

class Build(object):

    def __init__(self, ws, package=None, suite=None, arch=None, db=None):
        self.ws = ws
        if package and suite and arch:
            if not db:
                db = self.ws.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT action FROM build WHERE package='%s' and suite='%s' and suite='%s'" % (package,suite,arch))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Build (%s %s %s) does not exist.' % (package,suite,arch)
            self.package = package
            self.suite   = suite
            self.suite   = arch
            self.action  = row[0]
        else:
            self.package = None
            self.suite   = None
            self.arch    = None
            self.action  = None

    def delete(self, db=None):
        assert self.package and self.suite and self.arch, 'Cannot delete non-existing "%s %s %s"' % (self.package, self.suite, self.arch)
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Deleting build %s %s %s' % (self.package, self.suite, self.arch))
        cursor.execute("DELETE FROM build WHERE package='%s' and suite='%s' and arch='%s'" % (self.package,self.suite,self.arch))

        self.name  = None

        if handle_ta:
            db.commit()

    def insert(self, db=None):
        assert self.package and self.suite and self.arch, 'Cannot insert non-existing "%s %s %s"' % (self.package, self.suite, self.arch)
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug("Creating new build '%s %s %s %s'" % (self.package,self.suite,self.arch,self.action) )
        cursor.execute("INSERT INTO build VALUES ('%s','%s','%s','%s')" % (self.package,self.suite,self.arch,self.action))

        if handle_ta:
            db.commit()

    def update(self, db=None):
        assert self.package and self.suite and self.arch, 'Cannot update non-existing "%s %s %s"' % (self.package, self.suite, self.arch)
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.ws.log.debug('Updating build "%s %s %s %s"' % (self.package,self.suite, self.arch, self.action))
        cursor.execute("UPDATE build SET action='%s' WHERE package='%s' and suite='%s' and arch='%s'" %
                       (self.action,self.package,self.suite,self.arch))
 
        if handle_ta:
            db.commit()

    def select(cls, ws, db=None):
        if not db:
            db = ws.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT package, suite, arch, action FROM build")
        builds = []
        for package, suite, arch, action in cursor:
            build = cls(ws)
            build.package = package
            build.suite   = suite
            build.arch    = arch
            build.action   = action
            builds.append(build)
        return builds
    select = classmethod(select)

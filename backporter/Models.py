# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import sys
import re
import string
import apt_pkg
import datetime

from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Enum     import Enum

apt_pkg.init()

__all__ = ['Dist', 'DistType', 'Backport', 'BackportStatus','Source','Package','Job']

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
            cursor.execute("SELECT status, options, version, stamp FROM backport WHERE package='%s'" % (package))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Backport %s does not exist.' % name
            self.package = package
            self.status  = row[0]
            self.options = row[1]
            self.version = row[2]
            self.stamp   = row[3]
        else:
            self.package  = None
            self.status   = True
            self.options  = None
            self.version  = None
            self.stamp    = None

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
        cursor.execute("INSERT INTO backport VALUES ('%s',%d, '%s', '%s', '%s')" % (
                self.package,
                self.status,
                self.options,
                self.version,
                self.stamp))

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
        Logger().debug('Updating backport "%s %s"' % (self.package,self.version))
        cursor.execute("UPDATE backport SET status=%d, options='%s', version='%s', stamp='%s' WHERE package='%s'" % (
                self.status,
                self.options,
                self.version,
                self.stamp,
                self.package))

        self.cnx.commit()

    def select(cls, status=None):
        cursor = Database().get_cnx().cursor()
        if not status:
            cursor.execute("SELECT package, status, options, version, stamp FROM backport")
        else:
            cursor.execute("SELECT package, status, options, version, stamp FROM backport WHERE status=%d" % status)
        backports = []
        for package, status, options, version, stamp in cursor:
            b = cls()
            b.package = package
            b.status  = status
            b.options = options
            b.version = version
            b.stamp   = stamp
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
                if Source.compare(b, s) <= -1:
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
        return apt_pkg.VersionCompare(a.version, b.version)

class Package(object):

    def __init__(self, name=None, version=None):
        self.cnx = Database().get_cnx()
        if name != None and version != None:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT id, priority FROM package WHERE name='%s' and version='%s'" % (name, version))
            row = cursor.fetchone()
            if not row:
                raise Exception, 'Package %s does not exist.' % name
            self.id       = row[0]
            self.name     = name
            self.version  = version
            self.priority = row[1]
        else:
            self.id       = None
            self.name     = None
            self.version  = None
            self.priority = None

    def delete(self):
        assert self.id, 'Cannot deleting non-existent package'
        cursor = self.cnx.cursor()
        Logger().debug("Deleting package %d" % self.id)
        cursor.execute("DELETE FROM package WHERE id=%d" % self.id)
        self.cnx.commit()

    def insert(self):
        assert self.name and self.version, 'Cannot create package with no nameand version'
        cursor = self.cnx.cursor()
        Logger().debug("Creating new package %s %s" % (self.name, self.version))
        cursor.execute("INSERT INTO package (name, version, priority) VALUES ('%s','%s', '%s')" % (self.name, self.version, self.priority))
        self.cnx.commit()

    def update(self):
        assert self.id, 'Cannot update non-existent package'
        cursor = self.cnx.cursor()
        Logger().debug('Updating package %d' % self.id)
        cursor.execute("UPDATE package SET name='%s', version='%s', priority='%s' WHERE id=%d" % \
                           (self.name, self.version, self.priority, self.id))
        self.cnx.commit()

    def select(cls):
        cursor = Database().get_cnx().cursor()
        cursor.execute("SELECT id, name, version, priority FROM package")
        packages = []
        for id, name, version, priority in cursor:
            p = cls()
            p.id       = id
            p.name     = name
            p.version  = version
            p.priority = priority
            packages.append(p)
        return packages
    select = classmethod(select)

class Job(object):

    def __init__(self, package_id=None, dist=None, arch=None):
        self.cnx = Database().get_cnx()
        if package_id and dist and arch:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT status, mailto, package_id, dist, arch, creation_date, status_changed, build_start, build_end, host FROM job WHERE package_id=%d and dist='%s' and arch='%s'" % (package_id, dist, arch))
            row = cursor.fetchone()
            if not row:
                raise Exception, 'Job %d does not exist.' % id
            self.id             = id
            self.status         = row[0]
            self.mailto         = row[1]
            self.package_id     = row[2]
            self.dist           = row[3]
            self.arch           = row[4]
            self.creation_date  = row[5]
            self.status_changed = row[6]
            self.build_end      = row[7]
            self.build_start    = row[8]
            self.host           = row[9]
        else:
            self.status         = None
            self.mailto         = None
            self.package_id     = None
            self.dist           = None
            self.arch           = None
            self.creation_date  = None
            self.status_changed = None
            self.build_end      = None
            self.build_start    = None
            self.host           = None

    def delete(self):
        assert self.id, 'Cannot deleting non-existent job'
        cursor = self.cnx.cursor()
        Logger().debug("Deleting job %d" % self.id)
        cursor.execute("DELETE FROM job WHERE id=%d" % self.id)
        self.cnx.commit()

    def insert(self):
        assert self.package_id, 'Cannot create job with no package_id'
        assert self.dist,       'Cannot create job with no dist'
        assert self.arch,       'Cannot create job with no arch'
        cursor = self.cnx.cursor()
        Logger().debug("Creating new job %d" % self.package_id)
        cursor.execute("INSERT INTO job (status, package_id, dist, arch, creation_date) VALUES (%d, %d, '%s', '%s', '%s')" % (
                100, # Alwasy jobs in WAIT status
                self.package_id,
                self.dist,
                self.arch,
                datetime.datetime.now()))
        self.cnx.commit()

    def update(self):
        assert self.id, 'Cannot update non-existent job'
        cursor = self.cnx.cursor()
        Logger().debug('Updating job %d' % self.package_id)
        cursor.execute("UPDATE job SET status=%d, mailto='%s', package_id=%d, dist='%s', arch='%s', creation_date='%s', status_changed='%s', build_start='%s', build_end='%s', host='%s' WHERE id=%d" % (
                self.status,
                self.mailto,
                self.package_id,
                self.dist,
                self.arch,
                self.creation_date,
                self.status_changed,
                self.build_start,
                self.build_end,
                self.host,
                self.id))
        self.cnx.commit()

    def select(cls, package_id=None, dist=None, arch=None):
        cursor = Database().get_cnx().cursor()
        if package_id and dist and arch:
            cursor.execute("SELECT id, status, mailto, package_id, dist, arch, creation_date, status_changed, build_start, build_end, host FROM job WHERE package_id=%d and dist='%s' and arch='%s'" % (package_id, dist, arch))
        else:
            cursor.execute("SELECT id, status, mailto, package_id, dist, arch, creation_date, status_changed, build_start, build_end, host FROM job")
        jobs = []
        for id, status, mailto, package_id, dist, arch, creation_date, status_changed, build_start, build_end, host in cursor:
            j = cls()
            j.id       = id
            j.status = status
            j.mailto = mailto
            j.package_id = package_id
            j.dist = dist
            j.arch = arch
            j.creation_date = creation_date
            j.status_changed = status_changed
            j.build_start = build_start
            j.build_end = build_end
            j.host = host
            jobs.append(j)
        return jobs
    select = classmethod(select)

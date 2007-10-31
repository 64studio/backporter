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
import os
from rebuildd.RebuilddConfig import RebuilddConfig

from backporter.Database import Database
from backporter.BackporterConfig import BackporterConfig
from backporter.BackporterError import BackporterError
from backporter.Logger   import Logger
from backporter.Enum     import Enum


__all__ = ['Backport', 'BackportPolicy', 'Package', 'Job']

BackportPolicy = Enum('Dummy', 'Never', 'Once', 'Always', 'Smart')

#
# Backport
# 
class Backport(object):

    def __init__(self, pkg=None, dist=None):
        self.cnx  = Database().get_cnx()
        self.cols = Database().get_col('backport')
        if pkg and dist:
            cursor = self.cnx.cursor()
            cursor.execute(
                "SELECT %s FROM backport WHERE pkg='%s' and dist='%s'" % (
                    ",".join(self.cols),
                    pkg,dist))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Backport %s/%s does not exist.' % (pkg,dist)
            i = 0
            for col in self.cols:
                setattr(self, col, row[i])
                i += 1
            self.archs=eval(row[6])
        else:
            for col in self.cols:
                setattr(self, col, None)
            self.policy   = BackportPolicy.Smart.Value
            self.progress = -1
            self.archs    = []

    def delete(self):
        assert self.pkg and self.dist, 'Cannot deleting non-existent backport'
        cursor = self.cnx.cursor()
        Logger().debug('Deleting backport %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
        cursor.execute("DELETE FROM backport WHERE pkg='%s' and dist='%s'" % (self.pkg, self.dist))
        self.cnx.commit()

    def insert(self):
        assert self.pkg and self.dist, 'Cannot create backport with no pkg or no dist'
        cursor = self.cnx.cursor()
        Logger().debug('Creating backport %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
        cursor.execute('INSERT INTO backport (%s) VALUES ("%s", "%s", "%s", "%s", "%s", "%s", "%s", %d, %d)' % (
                ",".join(self.cols), self.pkg, self.dist, self.origin, self.bleeding, self.official,
                self.target, str(self.archs), self.progress, self.policy))
        self.cnx.commit()

    def update(self):
        assert self.pkg and self.dist, 'Cannot update backport with no pkg or no dist'
        cursor = self.cnx.cursor()
        Logger().debug('Updating backport %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
        cursor.execute(
            'UPDATE backport SET origin="%s", bleeding="%s", official="%s", target="%s", archs="%s", progress=%d, policy=%d WHERE pkg="%s" and dist="%s"' % (
                self.origin,
                self.bleeding,
                self.official,
                self.target,
                str(self.archs),
                self.progress,
                self.policy,
                self.pkg,
                self.dist))

        self.cnx.commit()

    def select(cls, orderBy=None, progress=None):
        cols  = ",".join(Database().get_col('backport'))
        stmt  = "SELECT %s FROM backport" % cols
        archs = RebuilddConfig().get('build', 'archs').split()
        if progress == 'complete':
            stmt += " WHERE progress = %d" % len(archs)
        if progress == 'partial':
            stmt += " WHERE progress >= 0 and progress < %d" % len(archs)
        if progress == 'null':
            stmt += " WHERE progress < 0"
        if orderBy:
            stmt += " ORDER BY %s" % orderBy
        cursor = Database().get_cnx().cursor()
        cursor.execute(stmt)
        backports = []
        for (pkg, dist, origin, bleeding, official, target, archs, progress, policy) in cursor:
            b = cls()
            b.pkg      = pkg
            b.dist     = dist
            b.origin   = origin
            b.bleeding = bleeding 
            b.official = official
            b.target   = target
            b.archs    = eval(archs)
            b.progress = progress
            b.policy   = policy
            backports.append(b)
        return backports
    select = classmethod(select)

    def jobs(cls, progress=None, status=None, orderBy=None):

        cols  = Database().get_col('backport')
        archs = RebuilddConfig().get('build', 'archs').split()
        select = "SELECT %s, job.id, job.status, job.arch FROM backport" % ", ".join(['backport.%s' % c for c in cols])
        join_pkg = " INNER JOIN package ON package.name=backport.pkg and package.version=backport.target and package.id=job.package_id"
        join_job = " INNER JOIN job ON job.dist=backport.dist"
        if status:
           join_job += " and job.status=%s" % status
        stmt = select + join_pkg + join_job

        if progress == 'complete':
            stmt += " WHERE backport.progress = %d" % len(archs)
        if progress == 'partial':
            stmt += " WHERE backport.progress >= 0 and backport.progress < %d" % len(archs)
        if progress == 'null':
            stmt += " WHERE backport.progress < 0"
        if orderBy:
            stmt += " ORDER BY %s" % orderBy

        cursor = Database().get_cnx().cursor()
        cursor.execute(stmt)

        backports = []
        
        for (pkg, dist, origin, bleeding, official, target, archs, progress, policy, job_id, job_status, job_arch) in cursor:
            b = cls()
            b.pkg      = pkg
            b.dist     = dist
            b.origin   = origin
            b.bleeding = bleeding 
            b.official = official
            b.target   = target
            b.archs    = eval(archs)
            b.progress = progress
            b.policy   = policy
            j = Job()
            j.id     = job_id
            j.status = job_status
            j.arch   = job_arch
            b.job    = j
            backports.append(b)
        return backports
    jobs = classmethod(jobs)

#
# Package
#
class Package(object):

    def __init__(self, name=None, version=None, id=None):
        self.cnx = Database().get_cnx()
        self.cols = Database().get_col('package')
        if name and not version or not name and version:
                raise BackporterError, 'Package selection by only name or version not valid'
        if name != None and version != None:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT id, priority FROM package WHERE name='%s' and version='%s'" % (name, version))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Package %s does not exist.' % name
            self.id       = row[0]
            self.name     = name
            self.version  = version
            self.priority = row[1]
        elif id != None:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT name, version, priority FROM package WHERE id=%d" % id)
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Package %s does not exist.' % name
            self.name     = row[0]
            self.version  = row[1]
            self.priority = row[2]
        else:
            self.id       = None
            self.name     = None
            self.version  = None
            self.priority = None

    def delete(self):
        assert self.id, 'Cannot deleting non-existent package'
        cursor = self.cnx.cursor()
        Logger().debug('Delating package %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
        cursor.execute("DELETE FROM package WHERE id=%d" % self.id)
        self.cnx.commit()

    def insert(self):
        assert self.name and self.version, 'Cannot create package with no nameand version'
        cursor = self.cnx.cursor()
        Logger().debug('Creating package %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
        cursor.execute("INSERT INTO package (name, version, priority) VALUES ('%s','%s', '%s')" % (self.name, self.version, self.priority))
        self.cnx.commit()

    def select(cls, name=None):
        cursor = Database().get_cnx().cursor()
        if name:
            cursor.execute("SELECT id, name, version, priority FROM package where name='%s'" % name)
        else:
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

#
# Job
#
class Job(object):

    def __init__(self, id=None):
        self.cols = Database().get_col('job')
        self.cnx = Database().get_cnx()
        if id:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT status, mailto, package_id, dist, arch, creation_date, status_changed, build_start, build_end, host FROM job WHERE id=%d" % (id))
            row = cursor.fetchone()
            if not row:
                raise BackporterError, 'Job %d does not exist.' % id
            self.id             = id
            self.status         = row[0]
            self.mailto         = row[1]
            self.package_id     = row[2]
            self.dist           = row[3]
            self.arch           = row[4]
            self.creation_date  = row[5]
            self.status_changed = row[6]
            self.build_start    = row[7]
            self.build_end      = row[8]
            self.host           = row[9]
        else:
            self.id             = None
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
        Logger().debug('Deleting job %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
        cursor.execute("DELETE FROM job WHERE id=%d" % self.id)
        self.cnx.commit()

    def insert(self):
        assert self.package_id, 'Cannot create job with no package_id'
        assert self.dist,       'Cannot create job with no dist'
        assert self.arch,       'Cannot create job with no arch'
        cursor = self.cnx.cursor()
        Logger().debug('Creating job %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
        cursor.execute("INSERT INTO job (status, package_id, dist, arch, creation_date) VALUES (?, ?, ?, ?, ?)", (
                self.status,
                self.package_id,
                self.dist,
                self.arch,
                datetime.datetime.now()))
        self.cnx.commit()

    def update(self):
        assert self.id, 'Cannot update non-existent job'
        cursor = self.cnx.cursor()
        Logger().debug('Updating job %s' % ", ".join([str(getattr(self,c)) for c in self.cols]))
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
        stmt = "SELECT id, status, mailto, package_id, dist, arch, creation_date, status_changed, build_start, build_end, host FROM job"
        if package_id and dist and arch:
            cursor.execute("%s WHERE package_id=%d and dist='%s' and arch='%s'" % (stmt, package_id, dist, arch))
        elif package_id:
            cursor.execute("%s WHERE package_id=%d" % (stmt, package_id))
        elif dist:
            cursor.execute("%s WHERE dist='%s'" % (stmt, dist))
        elif package_id:
            cursor.execute("%s WHERE package_id=%d" % (stmt, package_id))
        else:
            cursor.execute("%s" % stmt)
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

    def join(cls, dist=None, package=None):
        cursor = Database().get_cnx().cursor()
        stmt='SELECT job.id, package.name, package.version, job.arch, job.status FROM job INNER JOIN package ON job.package_id=package.id'
        if dist != None and package != None:
            cursor.execute("%s WHERE job.dist='%s' and package.name='%s' ORDER BY job.id DESC" % (stmt, dist, package))
        elif dist != None:
            cursor.execute("%s WHERE job.dist='%s' ORDER BY job.id DESC" % (stmt, dist))
        else:
            cursor.execute("%s ORDER BY job.id DESC" % stmt)
        jobs = []
        for id, package, version, arch ,status in cursor:
            j = cls()
            j.id       = id
            j.package = package
            j.version = version
            j.arch = arch
            j.status = status
            jobs.append(j)
        return jobs
    join = classmethod(join)

    def logfile(self):
        """Compute and return logfile name"""

        log_path = os.path.join(BackporterConfig().get('config', 'workspace'), 'log')
        date = self.creation_date.replace('-','').replace(':','').replace(' ','-')[0:15]
        build_log_file = "%s/%s_%s-%s-%s-%s.%s.log" % (log_path,
                                           self.package.name, self.package.version,
                                           self.dist, self.arch,
                                           date,
                                           self.id)
        return build_log_file

    def join(cls, progress=None, status=None, orderBy=None):

        cols  = Database().get_col('backport')
        archs = RebuilddConfig().get('build', 'archs').split()
        select = "SELECT %s, job.id, job.status, job.arch FROM job" % ", ".join(['backport.%s' % c for c in cols])
        join_pkg = " INNER JOIN package ON package.name=backport.pkg and package.version=backport.target and package.id=job.package_id"
        join_bkp = " INNER JOIN backport ON backport.dist=job.dist"
        if progress == 'complete':
            join_bkp += " and backport.progress = %d" % len(archs)
        if progress == 'partial':
            join_bkp += " and backport.progress >= 0 and backport.progress < %d" % len(archs)
        if progress == 'null':
            join_bkp += " and backport.progress < 0"

        stmt = select + join_pkg + join_bkp

        if status:
            stmt += " WHERE job.status=%s" % status
        if orderBy:
            stmt += " ORDER BY %s" % orderBy

        cursor = Database().get_cnx().cursor()
        cursor.execute(stmt)

        jobs = []
        
        for (pkg, dist, origin, bleeding, official, target, archs, progress, policy, job_id, job_status, job_arch) in cursor:
            j = cls()
            j.id     = job_id
            j.status = job_status
            j.arch   = job_arch
            b = Backport()
            b.pkg      = pkg
            b.dist     = dist
            b.origin   = origin
            b.bleeding = bleeding 
            b.official = official
            b.target   = target
            b.archs    = eval(archs)
            b.progress = progress
            b.policy   = policy
            j.backport = b
            jobs.append(j)
        return jobs
    join = classmethod(join)

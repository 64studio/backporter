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

from backporter.Database import Database
from backporter.BackporterConfig import BackporterConfig
from backporter.BackporterError import BackporterError
from backporter.Logger   import Logger
from backporter.Enum     import Enum

__all__ = ['Backport', 'BackportPolicy']

BackportPolicy = Enum('Dummy', 'Never', 'Once', 'Always', 'Smart')

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
        Logger().debug("Deleting backport '%s/%s'" % (self.pkg,self.dist))
        cursor.execute("DELETE FROM backport WHERE pkg='%s' and dist='%s'" % (self.pkg, self.dist))
        self.cnx.commit()

    def insert(self):
        assert self.pkg and self.dist, 'Cannot create backport with no pkg or no dist'
        cursor = self.cnx.cursor()
        Logger().debug("Creating new backport %s/%s" % (self.pkg, self.dist))
        cursor.execute('INSERT INTO backport (%s) VALUES ("%s", "%s", "%s", "%s", "%s", "%s", "%s", %d, %d)' % (
                ",".join(self.cols), self.pkg, self.dist, self.origin, self.bleeding, self.official,
                self.target, str(self.archs), self.progress, self.policy))
        self.cnx.commit()

    def update(self):
        assert self.pkg and self.dist, 'Cannot update backport with no pkg or no dist'
        cursor = self.cnx.cursor()
        Logger().debug('Updating backport "%s %s"' % (self.pkg,self.dist))
        cursor.execute(
            'UPDATE backport SET origin="%s", bleeding="%s", official="%s", target="%s", archs="%s", progress=%d, policy=%d WHERE pkg="%s" and dist="%s"' % (
                self.origin,
                self.bleeding,
                self.official,
                self.target,
                self.archs,
                self.progress,
                self.policy,
                self.pkg,
                self.dist))

        self.cnx.commit()

    def select(cls, orderBy=None):
        cursor = Database().get_cnx().cursor()
        cols = ",".join(Database().get_col('backport'))
        if orderBy:
            cursor.execute("SELECT %s FROM backport ORDER BY %s" % (cols, orderBy))
        else:
            cursor.execute("SELECT %s FROM backport" % cols)
        backports = []
        for (pkg, dist, origin, bleeding, official, target, archs, progress, policy) in cursor:
            b = cls()
            b.pkg      = pkg
            b.dist     = dist
            b.origin   = origin
            b.bleeding = bleeding 
            b.official = official
            b.target   = target
            b.archs    = archs
            b.progress = progress
            b.policy   = policy
            backports.append(b)
        return backports
    select = classmethod(select)

# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

from backporter.utils import *

__all__ = ['Suite', 'SuiteType']

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
        assert self.type, 'Cannot create suite with no type'
        assert self.url,  'Cannot create suite with no url'
        assert self.comp, 'Cannot create suite with no comp'
        self.name = self.name.strip()
        if not db:
            db = self.ws.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
#        self.db.log.debug("Creating new suite '%s'" % self.name)
#        print 'INSERT INTO suite VALUES (%s,%d,%s,%s)' % (self.name, 0, self.url, self.comp)
        cursor.execute("INSERT INTO suite VALUES ('%s',%d,'%s','%s')" % (self.name, 0, self.url, self.comp))

        if handle_ta:
            db.commit()

    def update(self, db=None):
        assert self.exists, 'Cannot update non-existent suite'
        assert self.name, 'Cannot update suite with no name'
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
#        def suite_order(v):
#            return (v.time or sys.maxint, embedded_numbers(v.name))
#        return sorted(suites, key=suite_order, reverse=True)
        return suites
    select = classmethod(select)

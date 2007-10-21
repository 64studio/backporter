# -*- coding: utf-8 -*-
# 
# Copyright (C) 2007 Free Ekanayaka

import re
import sys
import time

__all__ = ['Backport']

class Backport(object):

    def __init__(self, ws, name=None, db=None):
        self.ws = ws
        if name:
            if not db:
                db = self.ws.get_db_cnx()
            cursor = db.cursor()
            cursor.execute('SELECT status FROM backport WHERE name=%s', (name,))
            row = cursor.fetchone()
            if not row:
                raise TracError, 'Version %s does not exist.' % name
            self.name = self._old_name = name
            self.time = row[0] and int(row[0]) or None
            self.description = row[1] or ''
        else:
            self.name = None

    exists = property(fget=lambda self: self.name is not None)

    def delete(self, db=None):
        assert self.exists, 'Cannot deleting non-existent version'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Deleting version %s' % self.name)
        cursor.execute("DELETE FROM version WHERE name=%s", (self.name,))

        self.name = self._old_name = None

        if handle_ta:
            db.commit()

    def insert(self, db=None):
        assert not self.exists, 'Cannot insert existing version'
        assert self.name, 'Cannot create version with no name'
        self.name = self.name.strip()
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.debug("Creating new version '%s'" % self.name)
        cursor.execute("INSERT INTO version (name,time,description) "
                       "VALUES (%s,%s,%s)",
                       (self.name, self.time, self.description))

        if handle_ta:
            db.commit()

    def update(self, db=None):
        assert self.exists, 'Cannot update non-existent version'
        assert self.name, 'Cannot update version with no name'
        self.name = self.name.strip()
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Updating version "%s"' % self.name)
        cursor.execute("UPDATE version SET name=%s,time=%s,description=%s "
                       "WHERE name=%s",
                       (self.name, self.time, self.description,
                        self._old_name))
        if self.name != self._old_name:
            # Update tickets
            cursor.execute("UPDATE ticket SET version=%s WHERE version=%s",
                           (self.name, self._old_name))
            self._old_name = self.name

        if handle_ta:
            db.commit()

    def select(cls, ws, db=None):
        if not db:
            db = ws.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT name,time,description FROM version")
        versions = []
        for name, time, description in cursor:
            version = cls(env)
            version.name = name
            version.time = time and int(time) or None
            version.description = description or ''
            versions.append(version)
        def version_order(v):
            return (v.time or sys.maxint, embedded_numbers(v.name))
        return sorted(versions, key=version_order, reverse=True)
    select = classmethod(select)

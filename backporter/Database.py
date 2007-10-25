# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
from pysqlite2 import dbapi2 as sqlite

from backporter.Config import Config
from backporter.Logger import Logger

__all__ = ['Database']

##
## Helper classes
##

class Table(object):
    """Declare a table in a database schema."""

    def __init__(self, name, key=[]):
        self.name = name
        self.columns = []
        self.indices = []
        self.key = key
        if isinstance(key, basestring):
            self.key = [key]

    def __getitem__(self, objs):
        self.columns = [o for o in objs if isinstance(o, Column)]
        self.indices = [o for o in objs if isinstance(o, Index)]
        return self


class Column(object):
    """Declare a table column in a database schema."""

    def __init__(self, name, type='text', size=None, unique=False,
                 auto_increment=False):
        self.name = name
        self.type = type
        self.size = size
        self.auto_increment = auto_increment


class Index(object):
    """Declare an index for a database schema."""

    def __init__(self, columns):
        self.columns = columns

##
## Database schema
##

schema = [
    # Common
    Table('suite', key='name')[
        Column('name'),
        Column('type', type='int'),
        Column('url'),
        Column('comp')],
    Table('backport', key=('package'))[
        Column('package'),
        Column('status', type='int'),
        Column('options')],
    Table('source', key=('package', 'suite'))[
        Column('package'),
        Column('suite'),
        Column('version')],
]

url = {'debian':'http://ftp.debian.org/debian'}
#SuiteType.Released.Value,url['debian']
#SuiteType.Bleeding.Value,url['debian']
data = (('suite',
         ('name','type','url','comp'),
         (('etch',0,'main contrib non-free'),
          ('sid' ,1,'main contrib non-free'))),
        ('enum',
         ('type', 'name', 'value'),
         (('status', 'new', 1),('status', 'old', 0)))
        )

##
## Database class
##

class Database(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
        if cls._instance is None:  
           cls._instance = object.__new__(cls)  
           cls._instance.init(*args, **kwargs)
        return cls._instance  

    def init(self):
        self.path = Config().get('config', 'database') 
        if not os.path.isfile(self.path): # Create new db
            self.create()
        self.cnx = sqlite.connect(self.path)

    # Create all tables
    def create(self):
        Logger().debug("Creating new db at %s" % self.path)
        self.cnx = sqlite.connect(self.path)
        cursor = self.cnx.cursor()
        for table in schema:
            for stmt in self._to_sql(table):
                cursor.execute(stmt)
        self.cnx.commit()
        self.cnx.close()

    def get_cnx(self):
        return self.cnx

    # Generate SQL CREATE statements
    def _to_sql(self,table):
        sql = ["CREATE TABLE %s (" % table.name]
        coldefs = []
        for column in table.columns:
            ctype = column.type.lower()
            if column.auto_increment:
                ctype = "integer PRIMARY KEY"
            elif len(table.key) == 1 and column.name in table.key:
                ctype += " PRIMARY KEY"
            elif ctype == "int":
                ctype = "integer"
            coldefs.append("    %s %s" % (column.name, ctype))
        if len(table.key) > 1:
            coldefs.append("    UNIQUE (%s)" % ','.join(table.key))
        sql.append(',\n'.join(coldefs) + '\n);')
        yield '\n'.join(sql)
        for index in table.indices:
            yield "CREATE INDEX %s_%s_idx ON %s (%s);" % (table.name,
               '_'.join(index.columns), table.name, ','.join(index.columns))

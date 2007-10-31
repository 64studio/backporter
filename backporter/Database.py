# backporter - Backport debian packages
#
# (c) 2007 - Free Ekanayaka <free@64studio.com>
#
#   This software is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; version 2 dated June, 1991.
#
#   This software is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this software; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#

import os
import threading
from pysqlite2 import dbapi2 as sqlite
from rebuildd.RebuilddConfig import RebuilddConfig

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

backporter_schema = [
    # Common
    Table('backport', key=('pkg','dist'))[
        Column('pkg'),                 # Package name
        Column('dist'),                # Dist name
        Column('origin'),              # Dist name of the bleeding version
        Column('bleeding'),            # Most recent available version
        Column('official'),            # Official version of backport.pkg in backport.dist
        Column('target'),              # Version of the last scheduled backport
        Column('archs'),               # Architectures where backport.target is BUILD_OK
        Column('progress',type='int'), # Number backport.archs
        Column('policy',type='int')],  # Schedule policy
]

rebuildd_schema = [
    Table('job', key=('id'))[
        Column('id',type='integer'),
        Column('status',type='int'),
        Column('mailto'),
        Column('package_id', type='int CONSTRAINT package_id_exists REFERENCES package(id) ON DELETE CASCADE'),
        Column('dist'),
        Column('arch'),
        Column('creation_date', type='timestamp'),
        Column('status_changed', type='timestamp'),
        Column('build_start', type='timestamp'),
        Column('build_end', type='timestamp'),
        Column('host')],
    Table('package', key=('id'))[
        Column('id', type='integer'),
        Column('name'),
        Column('version'),
        Column('priority')],
]

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

    def init(self, path=None):
        if path:
            self.path = path
        else:
            self.path = RebuilddConfig().get('build', 'database_uri')[len('sqlite://'):]

        self.create(rebuildd_schema)
        self.create(backporter_schema)

    # Create all tables in schema
    def create(self, schema):
        cnx = self.get_cnx()
        cursor = cnx.cursor()
        for table in schema:
            cursor.execute('PRAGMA table_info (%s)' % table.name)
            if not cursor.fetchone():
                Logger().debug("Creating table %s at %s" % (table.name,self.path))
                for stmt in self._to_sql(table):
                    cursor.execute(stmt)
        cnx.commit()

    # Create all tables in schema
    def clean(self):
        cnx = self.get_cnx()
        cursor = cnx.cursor()
        for table in backporter_schema + rebuildd_schema:
            cursor.execute('PRAGMA table_info (%s)' % table.name)
            if cursor.fetchone():
                Logger().debug("Cleaning table %s at %s" % (table.name,self.path))
                cursor.execute('DELETE FROM %s' % table.name)
        cnx.commit()

    # Return a db connection
    def get_cnx(self):
        if not hasattr(self, 'cnx'):
            self.cnx = {}
        tname = threading.currentThread().getName()
        if self.cnx.has_key(tname):
            return self.cnx[tname]
        else:
            self.cnx[tname] = sqlite.connect(self.path, check_same_thread=False)
            return self.cnx[tname]

    # Return the columns of a table
    def get_col(self, name):
        for table in backporter_schema + rebuildd_schema:
            if table.name == name:
                return [column.name for column in table.columns]
        raise BackporterError, 'No table table named %s' % name

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

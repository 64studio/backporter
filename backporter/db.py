import os
from pysqlite2 import dbapi2 as sqlite

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

class Database:

    def __init__(self, ws):
        self.path = os.path.join(os.path.join(ws.path, 'db'), 'backporter.db')
        self.cnx = None

    def get_db_dir(self):
        """Return absolute path to the build directory."""
        return 

    def init_db(self, params={}):
        if os.path.exists(self.path):
                raise BackporterError, 'Database already exists at %s' % self.path
        os.makedirs(os.path.split(self.path)[0])
        cnx = self.get_connection()
        cursor = cnx.cursor()
        from backporter.db_default import schema
        for table in schema:
            for stmt in self.to_sql(table):
                cursor.execute(stmt)
        cnx.commit()

    def get_connection(self):
        if not self.cnx:
            self.cnx = sqlite.connect(self.path)
        return self.cnx

    def shutdown(self, tid=None):
        if self._cnx_pool:
            self._cnx_pool.shutdown(tid)
            if not tid:
                self._cnx_pool = None

    def _get_connector(self): ### FIXME: Make it public?
        scheme, args = _parse_db_str(self.connection_uri)
        candidates = {}
        connector = None
        for connector in self.connectors:
            for scheme_, priority in connector.get_supported_schemes():
                if scheme_ != scheme:
                    continue
                highest = candidates.get(scheme_, (None, 0))[1]
                if priority > highest:
                    candidates[scheme] = (connector, priority)
            connector = candidates.get(scheme, [None])[0]
        if not connector:
            raise TracError('Unsupported database type "%s"' % scheme)

        if scheme == 'sqlite':
            # Special case for SQLite to support a path relative to the
            # environment directory
            if args['path'] != ':memory:' and \
                   not args['path'].startswith('/'):
                args['path'] = os.path.join(self.env.path,
                                            args['path'].lstrip('/'))

        return connector, args

    def to_sql(self,table):
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


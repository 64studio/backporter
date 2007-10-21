# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import ConfigParser
import string
from backporter import db_default
from backporter.db import *

__all__ = ['Workspace']


class Workspace:

    def __init__(self, path, create=False):

        self.path = path
        self.db = Database(self)

        if create:
            self.create()
        else:
            self.verify()



    def create(self):
        """Create the basic directory structure of the workspace, initialize
        the database and populate the configuration file with default values."""
        def _create_file(fname, data=None):
            fd = open(fname, 'w')
            if data: fd.write(data)
            fd.close()

        # Create the directory structure
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        os.mkdir(self.get_log_dir())
        os.mkdir(self.get_build_dir())
        os.mkdir(self.get_apt_dir())

        # Setup the default configuration
        os.mkdir(os.path.join(self.path, 'conf'))
        _create_file(os.path.join(self.path, 'conf', 'backporter.ini'))
        self.setup_config()

        # Create the database
        self.db.init_db()

        db = self.get_db_cnx()
        cursor = db.cursor() #cursor.executemany
        for table, cols, vals in db_default.data:
            for val in vals:
                cursor.execute("INSERT INTO %s VALUES %s" % (table, val))
        db.commit()

        self._update_sample_config()

    def get_log_dir(self):
        """Return absolute path to the log directory."""
        return os.path.join(self.path, 'log')

    def get_build_dir(self):
        """Return absolute path to the build directory."""
        return os.path.join(self.path, 'build')

    def get_apt_dir(self):
        """Return absolute path to the build directory."""
        return os.path.join(self.path, 'apt')

    def setup_config(self, load_defaults=False):
        """Load the configuration file."""

        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.join(self.path, 'conf', 'backporter.ini'))

        for section in self.config.sections():
            for option in self.config.options(section):
                print " ", option, "=", self.config.get(section, option)

    def get_db_cnx(self):
        """Return a database connection from the connection pool."""
        return self.db.get_connection()

    def verify(self):
        """Verify that the provided path points to a valid Trac environment
        directory."""
        return
        fd = open(os.path.join(self.path, 'VERSION'), 'r')
        try:
            assert fd.read(26) == 'Trac Environment Version 1'
        finally:
            fd.close()

    # Internal methods

    def _update_sample_config(self):
        from ConfigParser import ConfigParser
        config = ConfigParser()

        sample = (
            ('distributions',
             {'debian':'http://ftp.debian.org/debian',
              'ubuntu':'http://archive.ubuntu.com/ubuntu'}),
            ('options', {'foo':'b'}))

        for section, options in sample:
            config.add_section(section)
            for name, value in options.items():
                config.set(section, name, value)
        filename = os.path.join(self.path, 'conf', 'backporter.ini.sample')
        try:
            fileobj = file(filename, 'w')
            try:
                config.write(fileobj)
                fileobj.close()
            finally:
                fileobj.close()
#            self.log.info('Wrote sample configuration file with the new '
#                          'settings and their default values: %s',
#                          filename)
        except IOError, e:
            self.log.warn('Couldn\'t write sample configuration file (%s)', e,
                          exc_info=True)

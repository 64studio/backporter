# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import ConfigParser
import string
import re

from backporter import db_default
from backporter.db import *
from backporter.utils import *
from backporter.suite import *
from backporter.package import *

__all__ = ['Workspace']

class Log:
    def debug(self,text):
        print 'D: %s' % text

class Workspace:

    def __init__(self, path, create=False):

        self.path = path
        self.db = Database(self)
        self.log = Log()

        if create:
            self.create()
        else:
            self.verify()

        # TODO these should be configurable
        self.archs = ['i386']

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
        os.mkdir(self.get_repo_dir())
        os.mkdir(self.get_build_dir())
        os.mkdir(self.get_apt_dir())
        os.mkdir(os.path.join(self.get_apt_dir(),'lists'))
        os.mkdir(os.path.join(self.get_apt_dir(),'lists','partial'))
        fd = open(os.path.join(self.get_apt_dir(), 'status'), 'w')
        fd.close()
        os.mkdir(os.path.join(self.get_apt_dir(),'partial'))

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

    def update(self):
        """Update APT lists"""
        self._gen_apt_conf()
#        os.system('apt-get update -c %s' %  os.path.join(self.get_apt_dir(),'apt.conf'))
        r = re.compile(' *([^ ]*)[ \|]*([^ ]*)[ \|]*[^ ]* *([^/]*)')
        for p in Package.select(self):
            madison = os.popen('apt-cache -c %s madison %s' %  (os.path.join(self.get_apt_dir(),'apt.conf'), p.name))
            for line in madison.readlines():
                m = r.match(line)
                v = Version(self)
                v.package = p.name
                v.suite   = m.group(3)
                v.value   = m.group(2)
                v.update()

    def _gen_apt_conf(self):
        sources = []
        for s in Suite.select(self):
            sources.append('deb-src %s %s %s' % (s.url, s.name, s.comp))
        write_data(os.path.join(self.get_apt_dir(),'sources.list'), "\n".join(sources))

        config = (('APT',
                   (('Get',
                     ['Only-Source "true"']),
                    ('GPGV',
                     ['TrustedKeyring "/etc/apt/trusted.gpg"']))),
                  ('Dir "%s"' % self.get_apt_dir(),
                   (('State "%s"' % self.get_apt_dir(),
                     ['Lists "%s"' % self.get_apt_dir() + '/lists',
                      'xstatus "xstatus"',
                      'userstatus "status.user"',
                      'status "%s"' % (self.get_apt_dir() + '/status'),
                      'cdroms "cdroms.list"']),
                    ('Etc "%s"' % self.get_apt_dir(),
                     ['SourceList "sources.list"',
                      'Main "apt.conf"',
                      'Preferences "preferences"',
                      'Parts "apt.conf.d/"']),
                    ('Cache "%s"' % self.get_apt_dir(),
                     ['Archives "%s"' % self.get_apt_dir(),
                      'srcpkgcache "srcpkgcache.bin"',
                      'pkgcache "pkgcache.bin"'])))
                  )
        lines = []
        for topl, midl in config:
            lines.append('%s\n{' % topl)
            for key, value in midl:
                lines.append('  %s\n  {\n    %s;\n  };' % (key,";\n    ".join(value)))
            lines.append('};')
        lines.append('quiet "0";');
        lines.append('APT::Cache-Limit "26777216";')

        write_data(os.path.join(self.get_apt_dir(),'apt.conf'), "\n".join(lines))

    def get_repo_dir(self):
        """Return absolute path to the repo directory."""
        return os.path.join(self.path, 'repo')

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
            ('pbuilder',
             {'root-command':'sudo',
              'foo':0}),
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

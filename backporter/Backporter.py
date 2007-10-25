# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import re

from backporter.Config   import Config
from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Models   import *


__all__ = ['Backporter']

class Backporter(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
       if cls._instance is None:  
          cls._instance = object.__new__(cls)  
          cls._instance.init(*args, **kwargs)
       return cls._instance  

    def init(self):
       return

    def dist_add(self, name, type, url, comp):
       s = Dist()
       s.name = name
       s.type = DistType.Bleeding.Value # FIX
       s.url  = url
       s.comp = comp
       s.insert()

    def dist_remove(self, name):
       s = Dist()
       s.name = name
       s.delete()

    def dist_update(self, name, type, url, comp):
       s = Dist()
       s.name = name
       s.type = DistType.Bleeding.Value # FIX
       s.url  = url
       s.comp = comp
       s.update()

    def backport_add(self, package, status, options):
       b = Backport()
       b.package = package
       b.type    = status
       b.options = options
       b.insert()

    def backport_remove(self, package):
       b = Backport()
       b.package = package
       b.delete()

    def backport_update(self, package, status, options):
       b = Backport()
       b.package = package
       b.status  = status
       b.options = options
       b.update()

    def source_add(self, package, dist, version):
       s = Source()
       s.package = package
       s.dist   = dist
       s.version = version
       s.insert()

    def source_remove(self, package, dist):
       s = Source()
       s.package = package
       s.dist = dist
       s.delete()
        
    def source_update(self, package, dist, version):
       s = Source()
       s.package = package
       s.dist  = dist
       s.version = version
       s.update()

    def update(self):
       self._gen_apt_sources_list()
       self._gen_apt_conf()
       self._gen_apt_hook()
       os.system('apt-get update -c %s' %  os.path.join(self._get_apt_dir(),'apt.conf'))
       r = re.compile(' *([^ ]*)[ \|]*([^ ]*)[ \|]*[^ ]* *([^/]*)')
       for b in Backport.select():
          madison = os.popen('apt-cache -c %s madison %s' %  (os.path.join(self._get_apt_dir(),'apt.conf'), b.package))
          for line in madison.readlines():
             m = r.match(line)
             s = Source(self)
             s.package = b.package
             s.dist    = m.group(3)
             s.version = m.group(2)
             s.update()

    def _get_apt_dir(self):
       return os.path.join(Config().get('config', 'workspace'), 'apt')

    def _gen_apt_sources_list(self):
       lines = []
       for d in Dist.select():
          lines.append('deb-src %s %s %s' % (d.url, d.name, d.comp))
       path = os.path.join(self._get_apt_dir(), 'sources.list')
       data = "\n".join(lines)
       self._write_file(path, data)

    def _gen_apt_conf(self):

       config = (('APT',
                  (('Get',
                    ['Only-Source "true"']),
                   ('GPGV',
                    ['TrustedKeyring "/etc/apt/trusted.gpg"']))),
                 ('Dir "%s"' % self._get_apt_dir(),
                  (('State "%s"' % self._get_apt_dir(),
                    ['Lists "%s"' % self._get_apt_dir() + '/lists',
                     'xstatus "xstatus"',
                     'userstatus "status.user"',
                     'status "%s"' % (self._get_apt_dir() + '/status'),
                     'cdroms "cdroms.list"']),
                   ('Etc "%s"' % self._get_apt_dir(),
                    ['SourceList "sources.list"',
                     'Main "apt.conf"',
                     'Preferences "preferences"',
                     'Parts "apt.conf.d/"']),
                   ('Cache "%s"' % self._get_apt_dir(),
                    ['Archives "%s"' % self._get_apt_dir(),
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

       path = os.path.join(Config().get('config', 'workspace'), 'apt', 'apt.conf')
       data = "\n".join(lines)

       self._write_file(path, data)

    def _gen_apt_hook(self):
        lines = []
        lines.append('#!/bin/sh')
        lines.append('apt-get update')
        path = os.path.join(Config().get('config', 'workspace'),'apt','hooks','D00apt_get_update')
        data = "\n".join(lines)
        self._write_file(path, data)
        os.system('chmod 755 %s' % path)

    def _write_file(self, path, data):
       try:
          f = file(path, 'w')
          try:
             f.write(data)
             f.close()
          finally:
             f.close()
       except IOError, e:
          Logger().warn('Couldn\'t write to file (%s)', e, exc_info=True)

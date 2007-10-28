# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import re
#import apt_pkg
import telnetlib
import socket

from backporter.BackporterConfig    import BackporterConfig
from backporter.Database import Database
from backporter.Logger   import Logger
from backporter.Models   import *

#apt_pkg.InitConfig()
#apt_pkg.InitSystem()

__all__ = ['Backporter']

class Backporter(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
       if cls._instance is None:  
          cls._instance = object.__new__(cls)  
          cls._instance.init(*args, **kwargs)
       return cls._instance  

    def init(self):

        # Create the directory structure
        for dir in [self._get_workspace_dir(),
                    self._get_apt_dir(),
                    self._get_sources_dir(),
                    self._get_chroots_dir(),
                    os.path.join(self._get_apt_dir(),'lists'),
                    os.path.join(self._get_apt_dir(),'lists','partial'),
                    os.path.join(self._get_apt_dir(),'hooks'),
                    os.path.join(self._get_apt_dir(),'partial')]:
            if not os.path.exists(dir):
                os.mkdir(dir)
        
        self._write_file(os.path.join(self._get_apt_dir(),'status'),'')

    def dist_list(self):
        data = []
        for d in Dist.select():
            data.append((d.name, DistType[d.type], d.url, d.comp))
        return data

    def dist_add(self, name, type, url, comp):
       s = Dist()
       s.name = name
       s.type = type
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
       s.type = type
       s.url  = url
       s.comp = comp
       s.update()

    def backport_list(self):
        data = []
        for b in Backport.select():
            data.append((b.package, BackportStatus[b.status], b.options))
        return data

    def backport_add(self, package, status, options):
       b = Backport()
       b.package = package
       b.status    = status
       b.options = options
       b.version = '0'
       b.stamp   = None
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
       os.system('apt-get update -c %s' %  self._get_apt_conf())
       r = re.compile(' *([^ ]*)[ \|]*([^ ]*)[ \|]*[^ ]* *([^/]*)')
       for b in Backport.select():
          madison = os.popen('apt-cache -c %s madison %s' %  (self._get_apt_conf(), b.package))
          for line in madison.readlines():
             m = r.match(line)
             s = Source(self)
             s.package = b.package
             s.dist    = m.group(3)
             s.version = m.group(2)
             s.update()

    def repack(self, package, dist):

        b = Backport(package)
        version = Source(package, b.bleeding()).version

        # Clean previous builds
        if os.path.exists(self._get_package_dir(package, version)):
            os.system('rm -R %s' %  self._get_package_dir(package, version))

        # Download the source
        if os.system ('cd %s && apt-get -c %s source %s=%s' % (
                self._get_sources_dir(),
                self._get_apt_conf(),
                package,
                version)) != 0:
            raise BackporterError, 'Source for %s %s could not be fetched.' % (p.name, v.value)

	if os.system ('echo | dch -b -v %s~%s1 --distribution %s-backports -c %s "Backport for %s"' % (
                version,
                dist,
                dist,
                self._get_changelog_file(package,version),
                dist)) != 0:
            raise BackporterError, 'Could not run dch for %s %s.' % (package, version)

	if os.system ('cd %s && dpkg-source -b %s' % (
                self._get_sources_dir(),
                '%s-%s' % (package, self._upstream_version(version)))) != 0:
            raise BackporterError, 'Source dir for %s %s not available.' % (p.name, v.value)

        if os.system('rm -R %s' %  self._get_package_dir(package, version)) != 0:
            raise BackporterError, 'Could not clean source package dir %' % self._get_package_dir(package, version)

    # Schedule build jobs for the packages that need to be backported
    def schedule(self):

        from backporter.BackporterScheduler import BackporterScheduler
        BackporterScheduler().schedule()

    def _get_workspace_dir(self):
        return BackporterConfig().get('config', 'workspace')

    def _get_sources_dir(self):
        return os.path.join(BackporterConfig().get('config', 'workspace'),'sources')

    def _get_chroots_dir(self):
        return os.path.join(BackporterConfig().get('config', 'workspace'),'chroot')

    def _get_apt_conf(self):
        return os.path.join(self._get_apt_dir(),'apt.conf')

    def _get_apt_dir(self):
       return os.path.join(BackporterConfig().get('config', 'workspace'), 'apt')

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

       path = os.path.join(BackporterConfig().get('config', 'workspace'), 'apt', 'apt.conf')
       data = "\n".join(lines)

       self._write_file(path, data)

    def _gen_apt_hook(self):
        lines = []
        lines.append('#!/bin/sh')
        lines.append('apt-get update')
        path = os.path.join(BackporterConfig().get('config', 'workspace'),'apt','hooks','D00apt_get_update')
        data = "\n".join(lines)
        self._write_file(path, data)
        os.system('chmod 755 %s' % path)

    def _get_package_dir(self, package, version):
        return os.path.join(
            self._get_sources_dir(),
            '%s-%s' % (package,self._upstream_version(version)))

    def _get_changelog_file(self, package, version):
        return os.path.join(
            self._get_package_dir(package, version),
            'debian',
            'changelog')

    def _get_dsc_file(self, package, version):
        return os.path.join(
            self._get_sources_dir(),
            '%s_%s.dsc' % (package,self._strip_epoch(version)))

    def _get_diff_file(self, package, version):
        return os.path.join(
            self._get_sources_dir(),
            '%s_%s.diff.gz' % (package,self._strip_epoch(version)))

    def _strip_epoch(self, version):
        if len(version.split(':')) >= 2:
            return "".join(version.split(':')[1:])
        else:
            return version

    def _strip_revision(self, version):
        return version.split('-')[0]

    def _upstream_version(self, version):
        return self._strip_revision(self._strip_epoch(version))

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

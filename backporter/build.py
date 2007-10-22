# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import string
import re

from backporter.utils import *
from backporter.model import *

__all__ = ['Builder']

# Suite specific builder
class Builder:

    def __init__(self,suite):

        if suite.type != SuiteType.Released.Value:
            raise BackporterError, 'Suite %s is not of type %s' % (suite.name, SuiteType.Released)

        self.suite = suite

        if not os.path.exists(self._get_build_dir()):
            os.makedirs(self._get_build_dir())
            os.makedirs(self._get_work_dir())
            os.makedirs(self._get_cache_dir())
            os.makedirs(self._get_log_dir())
            os.makedirs(self._get_result_dir())

    # Creates base.tgz
    def build(self):
        for a in self.suite.ws.archs:

            # Generate conf file
            self._gen_config_file(a)

            # Generate chroot if missing
            if not os.path.isfile(self._get_chroot_file(a)):
                self.suite.ws.log.info("Generating chroot for %s, this the right time for a coffee ;)")
                self._create_chroot(a)

            # Build scheduled packages
            for p in Package.select(self.suite.ws):
                v = Version(self.suite.ws, p.name, p.get_bleeding())
                showsrc = os.popen('apt-cache -c %s showsrc %s' % (
                        self.suite.ws.get_apt_conf(),
                        p.name))

                if string.find(showsrc.read(), 'Version: %s' % v.value) == -1:
                    raise BackporterError, 'Source for %s %s does not exist.' % (p.name, v.value)

                self._download_source(p,v)
                self._backport_source(p,v)
                self._build_source(p,v,a)

    # Build a package
    def _build_source(self, p, v, a):
        os.system('%s build --configfile %s %s' % (
                self._get_builder_cmd(),
                self._get_config_file(a),
                os.path.join(self._get_build_dir(),
                             '%s_%s~%s1.dsc' % (p.name,strip_epoch(v.value),self.suite.name))))

    def _download_source(self,p,v):

	if os.system ('cd %s && apt-get -c %s source %s=%s' % (
                self._get_build_dir(),
                self.suite.ws.get_apt_conf(),
                p.name,
                v.value)) != 0:
            raise BackporterError, 'Source for %s %s could not be fetched.' % (p.name, v.value)

    def _backport_source(self,p,v):

        changelog = os.path.join(
            self._get_build_dir(),
            '%s-%s' % (p.name,upstream_version(v.value)),
            'debian',
            'changelog')

	if os.system ('echo | dch -b -v %s~%s1 --distribution %s-backports -c %s "Backport for %s"' % (
                v.value,
                self.suite.name,
                self.suite.name,
                changelog,
                self.suite.name)) != 0:
            raise BackporterError, 'Could not run dch for %s %s.' % (p.name, v.value)

        os.remove(os.path.join(
                self._get_build_dir(),
                '%s_%s.dsc' % (p.name,strip_epoch(v.value))))
        os.remove(os.path.join(
                self._get_build_dir(),
                '%s_%s.diff.gz' % (p.name,strip_epoch(v.value))))

	if os.system ('cd %s && dpkg-source -b %s' % (
                self._get_build_dir(),
                '%s-%s' % (p.name, upstream_version(v.value)))) != 0:
            raise BackporterError, 'Source for %s %s could not be fetched.' % (p.name, v.value)

# rm -f ${PACKAGE}*.dsc ${PACKAGE}*.diff.gz
                
    # Return appropriate pbuilderrc
    def _gen_config_file(self, arch):
        config = (('BASETGZ', self._get_chroot_file(arch)),
                  ('BUILDPLACE', self._get_work_dir()),
                  ('BUILDRESULT', self._get_result_dir()),
                  ('MIRRORSITE', self.suite.url),
                  ('USEPROC', 'yes'),
                  ('USEDEVPTS','yes'),
                  ('USEDEVFS', 'no'),
                  ('DISTRIBUTION', self.suite.name),
                  ('COMPONENTS', '\"%s\"' % self.suite.comp),
                  ('APTCACHE', self._get_cache_dir()),
                  ('APTCACHEHARDLINK', 'yes'),
                  ('DEBBUILDOPTIONS','-b'),
                  ('BUILDUSERID','1234'),
                  ('BINDMOUNTS',''),
                  ('PKGNAME_LOGFILE','yes'),
                  ('DEBOOTSTRAPOPTS[0]', '--variant=buildd'),
)
        lines = []
        for name, value in config:
            lines.append('%s=%s' % (name, value))

        write_data(self._get_config_file(arch),  "\n".join(lines))

    def _get_config_file(self,arch):
        return os.path.join(self._get_build_dir(), 'pbuilderrc-%s' % arch)

    def _get_chroot_file(self,arch):
        return os.path.join(self._get_build_dir(), 'base-%s.tgz' % arch)

    def _get_build_dir(self):
        return os.path.join(self.suite.ws.get_build_dir(),self.suite.name)

    def _get_work_dir(self):
        return os.path.join(self._get_build_dir(),'work')

    def _get_cache_dir(self):
        return os.path.join(self._get_build_dir(),'cache')

    def _get_log_dir(self):
        return os.path.join(self._get_build_dir(),'log')

    def _get_result_dir(self):
        return os.path.join(self._get_build_dir(),'result')

    def _get_builder_cmd(self):
        return 'sudo /usr/sbin/pbuilder'

    def _create_chroot(self,arch):
        try:
            os.system('%s create --configfile %s' % (self._get_builder_cmd(), self._get_config_file(arch)))
        except IOError, e:
            self.log.warn('Couldn\'t create chroot (%s)', e, exc_info=True)

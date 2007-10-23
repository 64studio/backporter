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
        self.ws    = suite.ws

        if not os.path.exists(self._get_build_dir()):
            os.makedirs(self._get_build_dir())
            os.makedirs(self._get_work_dir())
            os.makedirs(self._get_cache_dir())
            os.makedirs(self._get_log_dir())
            os.makedirs(self._get_result_dir())

    # Creates base.tgz
    def build(self):
        for a in self.ws.archs:

            # Generate conf file
            self._gen_config_file(a)

            # Generate chroot if missing
            if not os.path.isfile(self._get_chroot_file(a)):
                self.ws.log.info("Generating chroot for %s/%s, this the right time for a coffee ;)" % (self.suite,a))
                self._create_chroot(a)

            # Build scheduled packages
            for p in Package.select(self.ws):
                v = Version(self.ws, p.name, p.get_bleeding())
                showsrc = os.popen('apt-cache -c %s showsrc %s' % (
                        self.ws.get_apt_conf(),
                        p.name))

                if string.find(showsrc.read(), 'Version: %s' % v.value) == -1:
                    raise BackporterError, 'Source for %s %s does not exist.' % (p.name, v.value)

                self._download_source(p,v)
                self._backport_source(p,v)
                if not self._build_source(p,v,a):
                    print "KO"
                self._check_result(p,v,a)

    # Build a package
    def _download_source(self,p,v):

	if os.system ('cd %s && apt-get -c %s source %s=%s' % (
                self._get_build_dir(),
                self.ws.get_apt_conf(),
                p.name,
                v.value)) != 0:
            raise BackporterError, 'Source for %s %s could not be fetched.' % (p.name, v.value)

    def _repack_source(self,p,v):

	if os.system ('echo | dch -b -v %s~%s1 --distribution %s-backports -c %s "Backport for %s"' % (
                v.value,
                self.suite.name,
                self.suite.name,
                self._get_changelog_file(p,v),
                self.suite.name)) != 0:
            raise BackporterError, 'Could not run dch for %s %s.' % (p.name, v.value)

        os.remove(self._get_dsc_file(p,v))
        os.remove(self._get_diff_file(p,v))

	if os.system ('cd %s && dpkg-source -b %s' % (
                self._get_build_dir(),
                '%s-%s' % (p.name, upstream_version(v.value)))) != 0:
            raise BackporterError, 'Source dir for %s %s not available.' % (p.name, v.value)

    def _build_source(self, p, v, a):
        vb = Version(self.ws)
        vb.value = v.value + '~%s1' % (self.suite.name)
        return os.system('%s build --configfile %s --logfile %s %s' % (
                self._get_builder_cmd(),
                self._get_config_file(a),
                self._get_log_file(p,vb,a),
                self._get_dsc_file(p,vb)))


    def _check_result(self, p, v, a):
        for line in open(self._get_log_file(p,v,a),).readlines():
            print line

    def _get_dsc_file(self, p, v):
        return os.path.join(
            self._get_build_dir(),
            '%s_%s.dsc' % (p.name,strip_epoch(v.value)))

    def _get_diff_file(self, p, v):
        return os.path.join(
            self._get_build_dir(),
            '%s_%s.diff.gz' % (p.name,strip_epoch(v.value)))

    def _get_changelog_file(self, p, v):
        return os.path.join(
            self._get_build_dir(),
            '%s-%s' % (p.name,upstream_version(v.value)),
            'debian',
            'changelog')

    def _get_log_file(self, p, v ,a):
        return os.path.join(
            self._get_result_dir(),
            '%s_%s~%s1_%s.build' % (
                p.name,
                strip_epoch(v.value),
                self.suite.name,
                a))

    # Return appropriate pbuilderrc
    def _gen_config_file(self, arch):
        config = (('BASETGZ', self._get_chroot_file(arch)),
                  ('BUILDPLACE', self._get_work_dir()),
                  ('BUILDRESULT', self._get_result_dir()),
                  ('MIRRORSITE', self.suite.url),
                  ('USEPROC', 'yes'),
                  ('USEDEVPTS','yes'),
                  ('USEDEVFS', 'no'),
                  ('HOOKDIR', self._get_hook_dir()),
                  ('DISTRIBUTION', self.suite.name),
                  ('COMPONENTS', '\"%s\"' % self.suite.comp),
                  ('APTCACHE', self._get_cache_dir()),
                  ('APTCACHEHARDLINK', 'yes'),
                  ('DEBBUILDOPTIONS','-b'),
                  ('BUILDUSERID','1234'),
                  ('BINDMOUNTS',''),
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
        return os.path.join(self.ws.get_build_dir(),self.suite.name)

    def _get_work_dir(self):
        return os.path.join(self._get_build_dir(),'work')

    def _get_cache_dir(self):
        return os.path.join(self._get_build_dir(),'cache')

    def _get_log_dir(self):
        return os.path.join(self._get_build_dir(),'log')

    def _get_result_dir(self):
        return os.path.join(self._get_build_dir(),'result')

    def _get_hook_dir(self):
        return os.path.join(self.ws.get_apt_dir(),'hooks')

    def _get_builder_cmd(self):
        return 'sudo /usr/sbin/pbuilder'

    def _create_chroot(self,arch):
        try:
            os.system('%s create  --configfile %s --debootstrapopts --arch=%s' % (
                    self._get_builder_cmd(),
                    self._get_config_file(arch),
                    arch))
        except IOError, e:
            self.log.warn('Couldn\'t create chroot (%s)', e, exc_info=True)

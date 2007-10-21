# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import os
import string

from backporter.utils import *
from backporter.suite import *

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

    # Creates base.tgz
    def create(self):
        for arch in self.suite.ws.archs:
            if os.path.isfile(self._get_chroot_file(arch)):
                raise BackporterError, 'Chroot already exists at %s' % self._get_build_dir()
            self._gen_config_file(arch)
            self._create_chroot(arch)

    # Return appropriate pbuilderrc
    def _gen_config_file(self, arch):
        config = (('BASETGZ', self._get_chroot_file(arch)),
                  ('BUILDPLACE', self._get_work_dir()),
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

    def _get_builder_cmd(self):
        return 'sudo /usr/sbin/pbuilder'

    def _create_chroot(self,arch):
        try:
            os.system('%s create --configfile %s' % (self._get_builder_cmd(), self._get_config_file(arch)))
        except IOError, e:
            self.log.warn('Couldn\'t create chroot (%s)', e, exc_info=True)

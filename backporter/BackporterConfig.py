# rebuildd - Debian packages rebuild tool
#
# (c) 2007 - Julien Danjou <acid@debian.org>
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

import ConfigParser
import os

__all__ = ['Config']

class BackporterConfig(object, ConfigParser.ConfigParser):
    """Main configuration singleton"""

    config_file = "/etc/backporter/backporter.conf"
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self, dontparse=False):
        ConfigParser.ConfigParser.__init__(self)

        # add default sections
        self.add_section('config')

        # add default values
        self.set('config', 'database',  '/var/lib/backporter')
        self.set('config', 'workspace', '/var/cache/backporter')
        self.set('config', 'log',       '/var/log/backporter')
        self.set('config', 'archs',     'i386 amd64')

        if not dontparse:
            self.reload()

    def reload(self):
        """Reload configuration file"""

        return self.read(self.config_file)

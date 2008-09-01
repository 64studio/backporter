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

import ConfigParser
import os

__all__ = ['BackporterConfig']

class BackporterConfig(object, ConfigParser.ConfigParser):
    """Main configuration singleton"""

    config_file = "/etc/backporter.conf"

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self, dontparse=False):
        ConfigParser.ConfigParser.__init__(self)

        # add default sections
        self.add_section('bleeding')
        self.add_section('released')
        self.add_section('http')

        # add default values
        self.set('bleeding', 'sid',  'deb-src http://ftp.debian.org/debian sid main')
        self.set('released', 'etch', 'deb-src http://ftp.debian.org/debian etch main')
        self.set('http',     'templates', '/usr/share/backporter/templates')
        self.set('http',     'ip',        '0.0.0.0')
        self.set('http',     'port',      '9997')

        if not dontparse:
            self.reload()

    def reload(self):
        """Reload configuration file"""

        return self.read(self.config_file)

    def dump(self):
        """Dump running configuration"""

        conf = ""
        for section in self.sections():
            conf += "[" + section + "]\n"
            for item, value in self.items(section):
                conf += "%s = %s\n" % (item, value)
            conf += "\n"
        return conf

    def save(self):
        """Save configuration file"""

        try:
            self.write(file(self.config_file, 'w'))
        except Exception, error:
            return False
        return True

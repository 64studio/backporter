# backporter - Tool for backporting Debian packages
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

"""backporter - Tool for backporting Debian packages"""

import sqlobject
import sys
import os

import warnings
warnings.simplefilter('ignore', FutureWarning)

from backporter.BackporterConfig import BackporterConfig
from backporter.Models import *
from rebuildd.RebuilddConfig import RebuilddConfig
from rebuildd.Rebuildd       import Rebuildd

class Backporterd(Rebuildd):

    _instance = None 
         
    def __new__(cls):  
        if cls._instance is None:  

            path = {}
            path['db']   = 'sqlite://' + os.path.join(BackporterConfig().get('config', 'database'), 'backporter.db')
            path['log']  = os.path.join(BackporterConfig().get('config', 'log'), 'rebuildd.log')
            path['ws']   = os.path.join(BackporterConfig().get('config', 'workspace'), 'sources')
            path['chroot']   = os.path.join(BackporterConfig().get('config', 'workspace'), 'chroots')
            path['logs'] = os.path.join(BackporterConfig().get('config', 'workspace'), 'log')
            path['hook'] = os.path.join(BackporterConfig().get('config', 'workspace'), 'apt', 'hooks')
            path['result'] = os.path.join(BackporterConfig().get('config', 'workspace'), 'result')
            path['apt'] = os.path.join(BackporterConfig().get('config', 'workspace'), 'apt')

            pbuilder = 'sudo pbuilder build --configfile %s/pbuilderrc-%%s-%%s %%s_%%s.dsc' % (path['apt'])
            dput     = 'dput local %s/%%s/%%s/%%s_%%s_%%s.changes'  % (path['result'])
            RebuilddConfig().config_file = "/dev/null"
            RebuilddConfig().set('build', 'database_uri', path['db'])
            RebuilddConfig().set('log', 'file', path['log'])
            RebuilddConfig().set('build', 'work_dir', path['ws'])
            RebuilddConfig().set('build', 'source_cmd', 'backporter repack %s %s %s')
            RebuilddConfig().set('build', 'build_cmd', pbuilder)
            RebuilddConfig().set('build', 'post_build_cmd', dput)
            RebuilddConfig().set('build', 'dists', " ".join([d.name for d in Dist.select()]))
            RebuilddConfig().set('build', 'archs', BackporterConfig().get('config', 'archs'))
            RebuilddConfig().set('build', 'max_threads', '1')
            RebuilddConfig().set('log', 'logs_dir', path['logs'])

            # Create missing directories
            if not os.path.exists(path['logs']):
                    os.mkdir(path['logs'])
            if not os.path.exists(path['ws']):
                    os.mkdir(path['ws'])
            if not os.path.exists(path['result']):
                    os.mkdir(path['result'])

            # Init the db
            if not os.path.isfile(os.path.join(BackporterConfig().get('config', 'database'), 'backporter.db')):
                try:
                    sqlobject.sqlhub.processConnection = \
                        sqlobject.connectionForURI(RebuilddConfig().get('build', 'database_uri'))
                    from rebuildd.Package import Package
                    from rebuildd.Job import Job
                    Package.createTable()
                    Job.createTable()
                except Exception, error:
                    print "E: %s" % error
                    return 1

            cls._instance = Rebuildd.__new__(cls)  

        return cls._instance  

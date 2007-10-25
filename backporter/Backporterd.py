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

from rebuildd.RebuilddConfig import RebuilddConfig
from rebuildd.Rebuildd       import Rebuildd
from backporter.Config       import Config

import sqlobject, sys

# Create database
def create_db():
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

    return 0

if len(sys.argv) == 2:
    if sys.argv[1] == "init":
        sys.exit(create_db())
    if sys.argv[1] == "dumpconfig":
        print RebuilddConfig().dump()
        sys.exit(0)
    if sys.argv[1] == "fix":
        Rebuildd().fix_jobs()
        sys.exit(0)

class Backporterd(Rebuildd):

    _instance = None 
         
    def __new__(cls):  
        if cls._instance is None:  
            cls._instance = Rebuildd.__new__(cls)  
            cls._instance.init()
        return cls._instance  

Backporterd().daemon()

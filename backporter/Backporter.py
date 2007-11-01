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

import os
import re
import telnetlib
import socket
import apt_pkg

from rebuildd.RebuilddConfig     import RebuilddConfig
from rebuildd.JobStatus          import JobStatus

from backporter.BackporterConfig import BackporterConfig
from backporter.Database         import Database
from backporter.Logger           import Logger
from backporter.Models           import *

apt_pkg.init()

__all__ = ['Backporter']

class Backporter(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
       if cls._instance is None:  
          cls._instance = object.__new__(cls)  
          cls._instance.init(*args, **kwargs)
       return cls._instance  

    def init(self):

        # Dists to consider as bleeding
        self.bdists = BackporterConfig().get('bleeding', 'dists').split()

        # Dists to consider as official releases
        self.rdists = RebuilddConfig().get('build', 'dists').split()
        self.archs = RebuilddConfig().get('build', 'archs').split()

    def list(self):
        data = []
        for b in Backport.select():
            data.append((b.pkg, b.dist, b.origin, b.bleeding, b.official, b.target,
                         b.archs, str(b.progress), BackportPolicy[b.policy]))
        return data

    def status(self, dist=None):
        backports = []
        
        d = Backport()
        d.pkg  = None
        d.dist = 'DUMMY'
        p = Backport()
        p.pkg      = None
        p.dist     = None
        p.status = {}

        for b in [d] + Backport.jobs(dist=dist, orderBy='backport.pkg,backport.dist,job.id DESC') + [d]:

            # We are starting a new backport group
            if b.pkg != p.pkg or b.dist != p.dist:

                # This is not a dummy element, update the data
                if p.pkg:
                    backports.append(p)

                p = Backport()
                p.pkg       = b.pkg
                p.dist      = b.dist
                p.origin    = b.origin
                p.bleeding  = b.bleeding
                p.official  = b.official
                p.target    = b.target
                p.archs     = b.archs
                p.policy    = b.policy
                p.progress  = b.progress
                p.status    = {}
                for arch in self.archs:
                    p.status[arch] = JobStatus.UNKNOWN

            # This is not a dummy element, update the status
            if p.pkg and p.status[b.job.arch] == JobStatus.UNKNOWN:
                p.status[b.job.arch] = b.job.status

        return backports

    def add(self, pkg, dist):
       b = Backport()
       if dist:
           dists = [dist]
       else:
           dists = self.rdists
       for dist in dists:
           b.pkg     = pkg
           b.dist    = dist
           b.bleeding = '0'
           b.official = '0'
           b.target   = '0'
           b.policy  = BackportPolicy.Smart.Value
           b.insert()

    def set(self, pkg, dist, opt, val):
       b = Backport(pkg, dist)
       if dist:
           dists = [dist]
       else:
           dists = self.rdists
       for dist in dists:
           b.pkg     = pkg
           b.dist    = dist
           setattr(b, opt, val)
           b.update()

    def remove(self, pkg, dist):
       if dist:
           dists = [dist]
       else:
           dists = self.rdists
       for dist in dists:
           b = Backport(pkg, dist)
           b.delete()

    # Compare to versions
    def _vercmp(self, a,b):
        return apt_pkg.VersionCompare(a, b)

    # Find out the bleeding dist
    def _bleeding(self, lookup):
        bdist = self.bdists[0]
        for dist in self.bdists:
            if self._vercmp(lookup[dist], lookup[bdist]) >= 1:
                bdist =dist
        return bdist

    # Download and repack a source
    def source(self, dist, pkg, ver, opts):

        # Download the source
        src_dir = None
        for line in os.popen('apt-get %s source %s=%s' % (opts or '', pkg, ver)).readlines():
            print line.strip()
            if line.startswith('dpkg-source: extracting %s in' % pkg):
                src_dir = line.split()[-1]
        if not src_dir:
            return 1

        # Change debian version to <ver>~<dist>1
	if os.system ('echo | dch -b -v %s~%s1 --distribution %s-backports -c %s "Backport for %s"' % (
                ver, dist, dist, os.path.join(src_dir,'debian','changelog'), dist)) != 0:
            return 1

        # Repack
	if os.system ('dpkg-source -b %s' % src_dir) != 0:
            return 1

        # Clean
        if os.system('rm -R %s' %  src_dir) != 0:
            return 1

    # Update versions from the APT database
    def update(self):

        # Init Python APT
        sources = apt_pkg.GetPkgSrcRecords()
        sources.Restart()
        lookup = {}
                
        # Iterate over backports
        p = Backport()
        for b in Backport.select(orderBy='pkg'):
            # New group of pkg backpors, look up what APT says..
            if b.pkg != p.pkg:
                p.pkg = b.pkg
                for dist in self.rdists + self.bdists:
                    lookup[dist] = '0'
                while sources.Lookup(b.pkg): # TODO: consider Architecture
                    ver  = sources.Version
                    dist = sources.Index.Describe.split()[1].split('/')[0]
                    lookup[dist] = ver
                bdist = self._bleeding(lookup)
                lookup['origin']   = bdist
                lookup['bleeding'] = lookup[bdist]

            # We have a new bleeding version is changed
            if self._vercmp(lookup['bleeding'], b.bleeding) >= 1:
                b.bleeding = lookup['bleeding']
                b.origin   = lookup['origin']
                b.progress = -1
                b.archs    = []
            # We have a new official version, maybe a stable update..
            if self._vercmp(lookup[b.dist], b.official) >= 1:
                b.official = lookup[b.dist]
                b.progress = -1
                b.archs    = []
            if b.progress == -1:
                b.update()

    # Schedule build jobs for the packages that need to be backported
    def schedule(self):

        # Init the counter of new BUILD_OK for each arch
        new_builds = set([])

        # Process BUILD_OK backports first
        p = Backport()
        p.pkg      = None
        p.dist     = None
        for b in Backport.jobs(progress='partial', status=JobStatus.BUILD_OK, orderBy='backport.pkg,backport.dist'):

            # Check if we are starting a new pkg group
            if b.pkg != p.pkg or b.dist != p.dist:
                p.pkg       = b.pkg
                p.dist      = b.dist
                p.origin    = b.origin
                p.bleeding  = b.bleeding
                p.official  = b.official
                p.target    = b.target
                p.archs     = b.archs
                p.policy    = b.policy
                p.progress  = b.progress

            # We have probably already considered this job
            if b.job.arch in p.archs:
                continue

            p.archs.append(b.job.arch)
            p.progress += 1
            p.update()
            new_builds.add(b.job.arch)

        # Let's see if we can re-trigger some DEPWAIT..
        p = Backport()
        p.pkg      = None
        p.target   = '0'
        p.arch     = None
        for b in Backport.jobs(progress='partial', status=JobStatus.DEPWAIT, orderBy='backport.pkg, backport.target, job.arch, job.id'):

            # Skip oldor schedules for the same backport
            if p.pkg == b.pkg and p.target == b.target and p.arch == b.arch:
                continue

            # There is already a BUILD_OK for this backport/arch, this is probably
            # a previously failed job
            if b.job.arch in b.archs:
                continue

            # Nothing has changed for this arch..
            if not b.job.arch in new_builds:
                continue

            # We are either Never or Once..
            if not (b.policy == BackportPolicy.Always.Value or b.policy == BackportPolicy.Smart.Value):
                continue
            
            # Let's try again!
            j = Job()
            j.status = JobStatus.WAIT
            j.package_id = Package(b.pkg,b.target).id # The package element MUST be there..
            j.dist = b.dist
            j.arch = b.job.arch
            j.insert()

        # Schedule new jobs
        for b in Backport.select(progress='null'):

            # Skip freezed backports
            if b.policy == BackportPolicy.Never.Value:
                continue
            # Did we run update() ?
            if b.bleeding == '0':
                continue
            # There something odd here..
            if b.bleeding == None:
                continue

            b.progress = 0
            b.target   = b.bleeding + "~%s1" % b.dist
            b.update()

            # Get the package element, create it if needed
            try:
                p = Package(b.pkg,b.target)
            except Exception, e:
                p = Package()
                p.name    = b.pkg
                p.version = b.target
                p.insert()
                p = Package(b.pkg,b.target) # This query could probably be avoided

            for arch in self.archs:

                # Add a new job
                j = Job()
                j.status = JobStatus.WAIT
                j.package_id = p.id
                j.dist = b.dist
                j.arch = arch
                j.insert()

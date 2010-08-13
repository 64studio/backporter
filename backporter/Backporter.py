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

import warnings
warnings.filterwarnings("ignore", module='apt')
del warnings

import apt_pkg
import apt

from rebuildd.RebuilddConfig     import RebuilddConfig
from rebuildd.JobStatus          import JobStatus, FailedStatus

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

        # Dist URIs
        self.uris = {}

        # Dists to consider as bleeding
        self.bdists = []
        for item in BackporterConfig().items('bleeding'):
            dist = item[0]
            uri  = item[1]
            self.bdists.append(dist)
            self.uris[dist] = uri

        # Dists to consider as bleeding
        self.rdists = []
        for item in BackporterConfig().items('released'):
            dist = item[0]
            uri  = item[1]
            self.rdists.append(dist)
            self.uris[dist] = uri

        self.archs = RebuilddConfig().get('build', 'more_archs').split()
        self.apt_dir = '/var/cache/backporter/'

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
        p.jobs = {}

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
                p.jobs    = {}
                for arch in self.archs:
                    p.jobs[arch] = Job()

            # This is not a dummy element, update the status
            if p.pkg and p.jobs[b.job.arch].status == JobStatus.UNKNOWN:
                p.jobs[b.job.arch] = b.job

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
           b.origin   = 'sid'
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
                bdist = dist
        return bdist

    # Download and repack a source
    def source(self, dist, pkg, ver, opts):

        # Download the source
        src_dir = None
        cmd='apt-get -c %s %s source %s=%s' % (self.apt_dir + 'apt.conf', opts or '', pkg, ver)

        for line in os.popen(cmd).readlines():
            print line.strip()
            if 'extracting %s in' % pkg in line:
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
        apt_dir = self.apt_dir
        apt_cnf = { 'Dir::Etc'             : apt_dir,
                    'Dir::Etc::sourcelist' : 'sources.list',
                    'Dir::State'           : apt_dir,
                    'Dir::State::lists'    : 'lists',
                    'Dir::State::status'   : 'status',
                    'Dir::Cache'           : apt_dir,
                    'Dir::Cache::archives' : apt_dir,
                    'Dir::Cache::srcpkgcache' : 'srcpkgcache.bin',
                    'Dir::Cache::pkgcache' : 'pkgcache.bin' }

        apt_cnf_file = open(apt_dir + 'apt.conf', 'w+')
        for key in apt_cnf:
            apt_pkg.Config.Set(key, apt_cnf[key])
            apt_cnf_file.write("%s \"%s\";\n" % (key, apt_cnf[key]))

        try:
            os.mkdir(apt_dir + apt_cnf['Dir::State::lists'])
            os.mkdir(apt_dir + apt_cnf['Dir::State::lists'] + '/partial')
            os.mkdir(apt_dir + '/partial')
            os.system('touch %s' % apt_dir + apt_cnf['Dir::State::status'])
        except OSError:
            pass

        apt_lst = open(apt_dir + apt_cnf['Dir::Etc::sourcelist'], 'w+')
        for dist in self.bdists + self.rdists:
            apt_lst.write(self.uris[dist] + '\n')
        apt_lst.close()

        c = apt.Cache()
        c.update(apt.progress.TextFetchProgress())

        sources = apt_pkg.GetPkgSrcRecords()
        sources.Restart()
        lookup = {}

        # Iterate over backports
        p = Backport()
        for b in Backport.select(orderBy='pkg'):

            # Skip backports with policy Never
            if (b.policy == BackportPolicy.Never.Value ):
                continue

            # New group of pkg backports, look up what APT says..
            if b.pkg != p.pkg:
                p.pkg = b.pkg
                for dist in self.rdists + self.bdists:
                    lookup[dist] = '0'
                while sources.Lookup(b.pkg): # TODO: consider Architecture
                    ver     = sources.Version
                    archive = sources.Index.Describe.split()[1].split('/')[0]
                    origin  = sources.Index.Describe.split()[0].rstrip('/')
                    # guess to which distribution does this APT record belong to
                    for dist in self.rdists + self.bdists:
                        dist_origin  = self.uris[dist].split()[1].rstrip('/')
                        dist_archive = self.uris[dist].split()[2]

                        if origin != dist_origin:
                            continue
                        if archive != dist_archive:
                            continue
                        lookup[dist] = ver
                        break

                lookup['bleeding'] = lookup[b.origin] # this can be '0'

            # We have a new bleeding version
            if self._vercmp(lookup['bleeding'], b.bleeding) != 0:
                b.bleeding = lookup['bleeding']
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
        building = set([])

        # Don't schedule process that are BUILDING
        for b in Backport.jobs(progress='partial', status=JobStatus.BUILDING, orderBy='backport.pkg,backport.dist'):
            building.add(b.pkg)

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
        p.job      = Job()
        for b in Backport.jobs(progress='partial', status=FailedStatus, orderBy='backport.pkg, backport.target, job.arch, job.id'):

            # Skip older schedules for the same backport
            if p.pkg == b.pkg and p.target == b.target and p.job.arch == b.job.arch:
                continue

            # New pkg group
            p.pkg      = b.pkg
            p.target   = b.target
            p.job.arch = b.job.arch

            # There is already a BUILD_OK for this backport/arch, this is probably a previously failed job
            if b.job.arch in b.archs:
                continue

            # We are already building
            if b.pkg in building:
                continue

            # We are either Never or Once..
            if not (b.policy == BackportPolicy.Always.Value or b.policy == BackportPolicy.Smart.Value):
                continue
            
            # Always means always
            if b.policy == BackportPolicy.Always.Value:
                Job.schedule(b.pkg, b.target, b.dist, b.job.arch)
                continue

            # Try to be smart
            if b.policy == BackportPolicy.Smart.Value:
                # Nothing has changed for this arch..
                if not b.job.arch in new_builds:
                    continue
                # We consider only depwaits
                if not b.job.status == JobStatus.DEPWAIT:
                    continue
                # Let's try again!
                Job.schedule(b.pkg, b.target, b.dist, b.job.arch)

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

            for arch in self.archs:
                Job.schedule(b.pkg, b.target, b.dist, arch)

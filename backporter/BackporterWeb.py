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

import web
import socket
import os

from backporter.Backporter          import Backporter
from backporter.BackporterScheduler import BackporterScheduler
from backporter.BackporterConfig    import BackporterConfig
from backporter.Models              import *
from backporter.Enum                import Enum

from rebuildd.JobStatus          import JobStatus

render = web.template.render(BackporterConfig().get('http', 'templates'),cache=False)

Color = Enum('Bleeding','Official','Newer','Backport','OutOfDate')

class RequestIndex:

    def GET(self):

        dists = Dist.select(DistType.Released.Value)

        print render.base(page=render.index(), \
                hostname=socket.gethostname(), \
                dists=dists)

def version_to_html(text):
    if text == None:
        return ' '
    if text == '0':
        return ' '
    return text[0:18]

def status_to_html(text):
    if text == 'UNKNOWN':
        return ' '
    if text[0:6] == 'BUILD_':
        return text[6:]
    else:
        return text

class RequestDist:

    def GET(self, dist, filter=None):

        dists = Dist.select(DistType.Released.Value)
        archs = BackporterConfig().get('config', 'archs').split()

        if not filter:
            status = BackportStatus.AutoUpdate.Value
        if filter == 'all':
            status = None

        tds = []
        # Iter over all backports
        for b in Backport.select(status=status):

            s = Source(b.package, dist)          # Official version
            t = Source(b.package, b.bleeding())  # Bleeding edge

            td = {}
            td['Package']  = (b.package, 'white')
            td['From']     = (b.bleeding(), b.bleeding())
            td['Bleeding'] = (Color.Bleeding, version_to_html(t.version))
            if Source.compare(t,s) == 0:
                td['Official'] = (Color.Bleeding, version_to_html(s.version))
            if Source.compare(t,s) >= 1:
                td['Official'] = (Color.Official, version_to_html(s.version))
            if Source.compare(t,s) <= -1:
                td['Official'] = (Color.Newer, version_to_html(s.version))

            b.version = None
            for j in Job.join(dist, b.package):
                if b.version == None:      # This must be the last scheduled job..
                    b.version = j.version
                    b.stamp   = j.creation_date
                if b.version != j.version: # Old job
                    break
                if not td.has_key(j.arch):
                    td[j.arch] = (j.id,status_to_html(JobStatus.whatis(j.status)))

            for a in archs:
                if not td.has_key(a):
                    td[a] = (0," ")

            if b.version == '%s~%s1' % (t.version, dist):
                td['Backport'] = (Color.Backport,  version_to_html(b.version))
            elif b.version == '%s~bpo.1' % t.version: # Support for old backports
                td['Backport'] = (Color.Backport,  version_to_html(b.version))
            elif b.version == '0' or b.version == None:
                td['Backport'] = (Color.Official,  version_to_html(b.version))
            else:
                td['Backport'] = (Color.OutOfDate, version_to_html(b.version))
            td['Mode'] = BackportStatus[b.status]
            td['Last schedule'] = b.stamp

            tds.append(td)

        print render.base(page=render.dist(tds=tds, dist=dist, archs=archs, filter=filter), \
                hostname=socket.gethostname(), dists=dists)

class RequestJob:

    def GET(self, jobid=None):

        dists = Dist.select(DistType.Released.Value)
        j = Job(id=int(jobid))
        j.package = Package(id=j.package_id)
        j.creation_date = j.creation_date[:-7]
        try:
            build_logfile = open(j.logfile(), "r")
            build_log = build_logfile.read()
        except IOError, error:
            build_log = "No build log available"
        print render.base(page=render.job(job=j, build_log=build_log), \
                hostname=socket.gethostname(), \
                title="job %s" % j.id,\
                dists=dists)

class RequestPackage:

    def GET(self, name=None):
        jobs = []

        dists = Dist.select(DistType.Released.Value)

        for p in Package.select(name=name):
            for j in Job.select(package_id=p.id):
                j.package = p
                jobs.append(j)
        print render.base(page=render.package(jobs=jobs), \
                hostname=socket.gethostname(), \
                title="package %s" % name, \
                dists=dists)

class BackporterWeb:
    """Main HTTP server"""

    urls = (
            '/', 'RequestIndex',
            '/dist/(.*)/(.*)', 'RequestDist',
            '/dist/(.*)', 'RequestDist',
            '/job/(.*)',  'RequestJob',
            '/package/(.*)',  'RequestPackage',
            )

    def __init__(self):
        Backporter()

    def start(self):

        """Run main HTTP server thread"""

        web.webapi.internalerror = web.debugerror
        web.httpserver.runsimple(web.webapi.wsgifunc(web.webpyfunc(self.urls, globals(), False)),
                                 (BackporterConfig().get('http', 'ip'),
                                  BackporterConfig().getint('http', 'port')))

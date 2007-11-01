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

from rebuildd.JobStatus          import JobStatus
from backporter.Backporter       import Backporter
from backporter.Models           import BackportPolicy
from backporter.BackporterConfig import BackporterConfig
from backporter.Enum             import Enum

render = web.template.render(BackporterConfig().get('http', 'templates'),cache=False)
dists = Backporter().rdists
archs = Backporter().archs

Color = Enum('Bleeding','Official','Newer','Backport','OutOfDate')

class RequestIndex:

    def GET(self):

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

    def GET(self, dist, policy=None):

        backports = Backporter().status(dist=dist)

        # Render integer values properly
        for b in backports:
            b.policy = BackportPolicy[b.policy]
            for arch in archs:
                b.status[arch] = status_to_html(JobStatus.whatis(b.status[arch]))

        print render.base(page=render.dist(backports=backports, dist=dist, archs=archs, policy=policy), \
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

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

from backporter.Backporter          import Backporter
from backporter.BackporterScheduler import BackporterScheduler
from backporter.BackporterConfig import BackporterConfig
from backporter.Models           import *

from rebuildd.JobStatus          import JobStatus

render = web.template.render(BackporterConfig().get('http', 'templates'),cache=False)

class RequestIndex:

    def GET(self):

        dists = Dist.select(DistType.Released.Value)

        print render.base(page=render.index(), \
                hostname=socket.gethostname(), \
                dists=dists)

def boldgreen(text):
    return '<b><font color="green">%s</font></b>' % text

def version_to_html(text):
    if text == '0':
        return '-'
    else:
        return text

class RequestDist:


    def GET(self, dist):

        dists = Dist.select(DistType.Released.Value)
        archs = BackporterConfig().get('config', 'archs').split()

        backports = []

        for b in Backport.select():

            s = Source(b.package, dist)
            b.origin   = b.bleeding()
            b.target   = version_to_html(Source(b.package, b.bleeding()).version)
            b.released = version_to_html(s.version)
            b.backport = '%s~%s1' % (b.target, dist)
            b.build    = {}

            for a in archs:
                status = BackporterScheduler().job_status(b.package, b.backport, dist, a)
                b.build[a] = JobStatus.whatis(status[1])

            backports.append(b)

        columns = ['Package'
                   'From'
                   'Bleeding'
                   'Released'
                   'Backport']

        print render.base(page=render.dist(backports=backports, dist=dist, archs=archs, columns=columns), \
                hostname=socket.gethostname(), dists=dists)


class BackporterWeb:
    """Main HTTP server"""

    urls = (
            '/', 'RequestIndex',
            '/dist/(.*)', 'RequestDist',
            )

    def __init__(self):
        Backporter()

    def start(self):

        """Run main HTTP server thread"""

        web.webapi.internalerror = web.debugerror
        web.httpserver.runsimple(web.webapi.wsgifunc(web.webpyfunc(self.urls, globals(), False)),
                                 (BackporterConfig().get('http', 'ip'),
                                  BackporterConfig().getint('http', 'port')))

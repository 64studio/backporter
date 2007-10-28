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
from backporter.BackporterConfig    import BackporterConfig
from backporter.Models              import *
from backporter.Enum                import Enum

#from rebuildd.JobStatus          import JobStatus

render = web.template.render(BackporterConfig().get('http', 'templates'),cache=False)

Color = Enum('Bleeding','Official','Newer','Backport','OutOfDate')

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
        return text[0:15]

def status_to_html(text):
    if text == 'UNKNOWN':
        return '-'
    else:
        return text

class RequestDist:

    def GET(self, dist):

        dists = Dist.select(DistType.Released.Value)
        archs = BackporterConfig().get('config', 'archs').split()

        tds = []

        # Iter over all backports
        for b in Backport.select():

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
            if b.version == '%s~%s1' % (t.version, dist):
                td['Backport'] = (Color.Backport,  version_to_html(b.version))
            elif b.version == '0':
                td['Backport'] = (Color.Official,  version_to_html(b.version))
            else:
                td['Backport'] = (Color.OutOfDate, version_to_html(b.version))
            td['Last schedule'] = b.stamp[:-7]

#            try:
                # Check if we tried already
#                p = Package(b.package, t.version)
#            except Exception, e:
#                p = Package()

            for a in archs:
#                status = BackporterScheduler().job_status(b.package, b.version, dist, a)
#                td[a] = status_to_html(JobStatus.whatis(status[1]))
                td[a] = "-"
            tds.append(td)

        print render.base(page=render.dist(tds=tds, dist=dist, archs=archs), \
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


#select package.name, package.version, job.arch ,job.status from package inner join job on package.id=job.package_id where job.dist='etch';

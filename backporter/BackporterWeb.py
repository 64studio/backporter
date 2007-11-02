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
from rebuildd.RebuilddConfig     import RebuilddConfig
from rebuildd.Rebuildd           import Rebuildd
from rebuildd.RebuilddHTTPServer import RequestPackage, RequestArch, RequestJob, RequestGraph
from backporter.Backporter       import Backporter
from backporter.Models           import BackportPolicy
from backporter.BackporterConfig import BackporterConfig
from backporter.Enum             import Enum

render = web.template.render(RebuilddConfig().get('http', 'templates_dir'),cache=False)
bp_render = web.template.render(BackporterConfig().get('http', 'templates'),cache=False)
dists = Backporter().rdists
archs = Backporter().archs

Color = Enum('Bleeding','Official','Newer','Backport','OutOfDate')

class RequestIndex:

    def GET(self):

        print bp_render.base(page=render.index(), \
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

class RequestBackport:

    def GET(self, dist, policy=None):

        backports = Backporter().status(dist=dist)

        # Render integer values properly
        for b in backports:
            b.policy = BackportPolicy[b.policy]
            for arch in archs:
                b.jobs[arch].status = status_to_html(JobStatus.whatis(b.jobs[arch].status))

        print bp_render.base(page=bp_render.backport(backports=backports, dist=dist, archs=archs, policy=policy), \
                hostname=socket.gethostname(), dists=dists)

class BackporterWeb:
    """Main HTTP server"""

    urls = (
            '/', 'RequestIndex',
            '/backport/(.*)/(.*)', 'RequestBackport',
            '/backport/(.*)', 'RequestBackport',
            '/job/(.*)', 'RequestJob',
            '/dist/(.*)/arch/(.*)', 'RequestArch',
            )

    def __init__(self):
        Backporter()
        Rebuildd()

    def start(self):

        """Run main HTTP server thread"""

        web.webapi.internalerror = web.debugerror
        web.httpserver.runsimple(web.webapi.wsgifunc(web.webpyfunc(self.urls, globals(), False)),
                                 (BackporterConfig().get('http', 'ip'),
                                  BackporterConfig().getint('http', 'port')))

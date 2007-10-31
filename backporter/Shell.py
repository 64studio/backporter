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

import cmd
import sys
from pysqlite2.dbapi2 import IntegrityError

from backporter.Backporter        import Backporter
from backporter.BackporterError   import BackporterError
from backporter.Models            import *
from rebuildd.RebuilddConfig      import RebuilddConfig

class Shell(cmd.Cmd):
 
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt     = 'Backporter> '
        self.doc_header = 'Commands (type help <topic>):'
        self.undoc_header = ''
        self.ruler = ''
        self.dists = RebuilddConfig().get('build','dists').split()

    def onecmd(self, line):
        if line == 'help':
            self.help_help(line)
            return
        return cmd.Cmd.onecmd(self, line)

    ##
    ## Available Commands
    ##

    ##  Help
    _help_help = [('help', 'Show documentation')]

    def do_help(self, line):
        arg = self._tokenize(line)
        for help in getattr(self, "_help_" + arg[0]):
            self._print_help(help)

    def help_help(self,line):
        print self.doc_header
        print

        for name in self.get_names():
            if not name[0:3] == 'do_':
                continue
            if name in ['do_EOF', 'do_help']:
                continue
            print "   %s" % name[3:]

    ## Add, set, remove backports
    _help_list   = [('list', 'Show backports')]
    _help_add    = [('add [-d <dist>]', 'Add a backport')]
    _help_set    = [('set [-d <dist>] <pkg> policy Never|Once|Always|Smart', 'Set backport options ')]

    def _parse_cmd(self, line):
        arg = self._tokenize(line)
        if not len(arg) >= 1:
            self._exit_with_error('Wrong syntax')
        if arg[0] == '-d':
            if not len(arg) > 2:
                self._exit_with_error('Wrong syntax')
            dist = arg[1]
            if not dist in self.dists:
                self._exit_with_error('Unknown distribution "%s"' % dist)
            pkg  = arg[2]
            if len(arg) > 3:
                rest = arg[3:]
            else:
                rest = []
        else:
            dist = None
            pkg = arg[0]
            if len(arg) > 1:
                rest = arg[1:]
            else:
                rest = []
                
        return (pkg, dist, rest)

    def do_add(self, line):
        (pkg, dist, rest) = self._parse_cmd(line)
        try:
            Backporter().add(pkg,dist)
        except IntegrityError, e:
            self._exit_with_error('Field exists')

    def do_set(self, line):
        (pkg, dist, rest) = self._parse_cmd(line)
        if len(rest) != 2:
            self._exit_with_error('Wrong syntax')
        if rest[0] in ['policy']:
            opt = rest[0]
            val = getattr(getattr(BackportPolicy, rest[1]), 'Value')
            Backporter().set(pkg, dist, opt, val)
            return 1
        self._exit_with_error('Unknown option')
        

    def do_list(self, arg):
        fields = ['Package', 'Dist', 'Origin', 'Bleeding', 'Official', 'Target', 'Archs', 'Progress', 'Policy']
        self._print_listing(fields, Backporter().list())

    def do_remove(self, line):
        (pkg, dist, rest) = self._parse_cmd(line)
        try:
            Backporter().remove(pkg,dist)
        except BackporterError, e:
            self._exit_with_error(e.message)

    ## Download and repack source
    _help_source = ('source -d <dist> <pkg>=<ver> [-- <apt-get options>]', 'Download and repack a source package')

    def do_source(self, line):
        arg = self._tokenize(line)
        if not len(arg) >= 3:
            self._exit_with_error('Wrong syntax')
        if not arg[0] == '-d':
            self._exit_with_error('Wrong syntax')
        if not arg[1] in self.dists:
            self._exit_with_error('Unknown distribution "%s"' % arg[1])
        if not len(arg[2].split('=')) == 2:
            self._exit_with_error('Wrong package or version "%s"' % arg[2])
        if len(arg) >= 4 and not arg[3] == '--':
            self._exit_with_error('Wrong syntax')

        dist = arg[1]
        pkg  = arg[2].split('=')[0]
        ver  = arg[2].split('=')[1]
        if ver.endswith('~%s1' % dist):
            ver = ver[:-len('~%s1' % dist)]
        if len(arg) >= 5:
            opts = " ".join(arg[4:])
        else:
            opts = None

        return Backporter().source(dist, pkg, ver, opts)

    ## Update versions
    _help_update = [('update', 'Update versions from APT')]

    def do_update(self, line):
        Backporter().update()


    ## Schedule new jobs
    _help_schedule = [('schedule', 'Schedule new jobs')]

    def do_schedule(self, line):
        Backporter().schedule()

    ## Quit

    def do_EOF(self, line):
        print
        sys.exit()

    ##
    ## Utility methods
    ##

    def _tokenize(self, line):
        return line.split()

    def _print_help(self, help):
        print '%s - %s' % (help[0], help[1])

    def _exit_with_error(self, error):
        print 'E: %s' % error
        sys.exit(1)

    def _print_listing(self, headers, data, sep=' ', decor=True):
        cons_charset = sys.stdout.encoding
        ldata = list(data)
        if decor:
            ldata.insert(0, headers)
        print
        colw = []
        ncols = len(ldata[0]) # assumes all rows are of equal length
        for cnum in xrange(0, ncols):
            mw = 0
            for cell in [unicode(d[cnum]) or '' for d in ldata]:
                if len(cell) > mw:
                    mw = len(cell)
            colw.append(mw)
        for rnum in xrange(len(ldata)):
            for cnum in xrange(ncols):
                if decor and rnum == 0:
                    sp = ('%%%ds' % len(sep)) % ' '  # No separator in header
                else:
                    sp = sep
                if cnum + 1 == ncols:
                    sp = '' # No separator after last column
                pdata = ((u'%%-%ds%s' % (colw[cnum], sp)) 
                         % (ldata[rnum][cnum] or ''))
                if cons_charset and isinstance(pdata, unicode):
                    pdata = pdata.encode(cons_charset, 'replace')
                print pdata,
            print
            if rnum == 0 and decor:
                print ''.join(['-' for x in
                               xrange(0, (1 + len(sep)) * cnum + sum(colw))])
        print

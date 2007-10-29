#!/usr/bin/env python

import cmd
import sys
from backporter.Backporter import Backporter
from backporter.Models     import BackportStatus, DistType

class Shell(cmd.Cmd):
 
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt     = 'Backporter> '
        self.doc_header = 'Commands (type help <topic>):'
        self.undoc_header = ''
        self.ruler = ''

    def onecmd(self, line):
        if line == 'help':
            self.help_help(line)
            return
        cmd.Cmd.onecmd(self, line)

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

    ## Dist
    _help_dist_list   = ('dist list', 'Show dists')
    _help_dist_chroot = ('dist chroot [<name>]', 'Creates build chroot')
    _help_dist_add    = ('dist add <name> <type> <url> <comp>', 'Add dist')
    _help_dist_remove = ('dist remove <name>', 'Remove dist')
    _help_dist = [_help_dist_list,
                  _help_dist_chroot,
                  _help_dist_remove,
                  _help_dist_add]

    def do_dist(self, line):
        arg = self._tokenize(line)
        if len(arg) == 0:
            return self.do_help('dist')
        return getattr(self, "_do_dist_" + arg[0])(arg[1:])

    def _do_dist_list(self, arg):

        self._print_listing(['Name', 'Type', 'Url','Components'], Backporter().dist_list())

    def _do_dist_add(self, arg):

        if not len(arg) >= 4:
            return self._print_help(self._help_dist_add)

        Backporter().dist_add(arg[0], arg[1], arg[2], " ".join(arg[3:]))

    def _do_dist_remove(self, arg):

        if not len(arg) == 1:
            return self._print_help(self._help_dist_add)

        Backporter().dist_remove(arg[0])

    ## Backports
    _help_backport_list   = ('backport list', 'Show backports')
    _help_backport_add    = ('backport add <package> [<mode>]', 'Add a backport')
    _help_backport_set    = ('backport set <package> [arch <arch>|dist <dist>]', 'Set backport options ')
    _help_backport_remove = ('backport remove <package>', 'Remove a backport')
    _help_backport = [_help_backport_list,
                  _help_backport_remove,
                  _help_backport_add, _help_backport_set]

    def do_backport(self, line):
        arg = self._tokenize(line)
        if len(arg) == 0:
            return self.do_help('backport')
        return getattr(self, "_do_backport_" + arg[0])(arg[1:])

    def _do_backport_list(self, arg):

        self._print_listing(['Package', 'Status', 'Options'], Backporter().backport_list())

    def _do_backport_add(self, arg):

        if not len(arg) >= 1:
            return self._print_help(self._help_backport_add)

        package = arg[0]
        if len(arg) >= 2:
            status = BackportStatus[arg[1]].Value # FIX
        else:
            status =  BackportStatus.AutoUpdate.Value
        if len(arg) >= 3:
            options = arg[2]
        else:
            options = None

        Backporter().backport_add(package, status, options)

    def _do_backport_set(self, arg):

        if not len(arg) in [3,5]:
            return self._print_help(self._help_backport_set)

        if not arg[1] in ['arch','dist']:
            return self._print_help(self._help_backport_set)

        pkg = arg[0]
        key = arg[1]
        val = arg[2]

        options = {}
        options[key] = val

        if len(arg) > 3:
            if arg[3] not in ['arch','dist']:
                return self._print_help(self._help_backport_options)
            key = arg[3]
            val = arg[4]
            options[key] = val

        Backporter().backport_update(pkg, options=options)

    def _do_backport_remove(self, arg):

        if not len(arg) == 1:
            return self._print_help(self._help_backport_add)

        Backporter().backport_remove(arg[0])

    ## Jobs
    _help_job_list   = ('job list <dist>', 'Show jobs for <dist>')
    _help_job = [_help_job_list]

    def do_job(self, line):
        arg = self._tokenize(line)
        if len(arg) == 0:
            return self.do_help('job')
        return getattr(self, "_do_job_" + arg[0])(arg[1:])

    def _do_job_list(self, arg):

        if len(arg) != 1:
            return self._print_help(self._help_job_list)            
        self._print_listing(['Job', 'Package', 'Version', 'Arch', 'Status'], Backporter().job_list(arg[0]))

    ## Download and repack source
    _help_repack = [('repack <name> <dist>', 'Download and repack a source package')]

    def do_repack(self, line):
        arg = self._tokenize(line)
        if not len(arg) >= 2:
            return self._print_help(self._help_repack)
        Backporter().repack(arg[1], arg[0])

    ## Update apt lists
    _help_update = [('update', 'Update APT lists')]

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

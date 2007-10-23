# -*- coding: utf-8 -*-
# 
# Copyright (C) 2007 Free Ekanayaka

import cmd
import getpass
import os
import shlex
import shutil
import StringIO
import sys
import time
import traceback
import urllib
import locale

import backporter
from backporter.ws import Workspace
from backporter.model import *
from backporter.build import *

class BackporterAdmin(cmd.Cmd):
    intro = ''
    license = backporter.__license_long__
    doc_header = 'Backporter Admin Console %(ver)s\n' \
                 'Available Commands:\n' \
                 % {'ver':backporter.__version__ }
    ruler = ''
    prompt = "Backporter> "
    __ws = None
    _date_format = '%Y-%m-%d'
    _datetime_format = '%Y-%m-%d %H:%M:%S'
    _date_format_hint = 'YYYY-MM-DD'

    def __init__(self, envdir=None):
        cmd.Cmd.__init__(self)
        self.interactive = False
        if envdir:
            self.env_set(os.path.abspath(envdir))
        self._permsys = None

    def onecmd(self, line):
        cmd.Cmd.onecmd(self, line) ### ENABLE DEBUG
        return 0
        """`line` may be a `str` or an `unicode` object"""
        try:
            line = line.replace('\\', '\\\\')
            rv = cmd.Cmd.onecmd(self, line) or 0
        except SystemExit:
            raise
        except Exception, e:
            print>>sys.stderr, 'Command failed: %s' % e
            rv = 2
        if not self.interactive:
            return rv

    def run(self):
        self.interactive = True
        print 'Welcome to backporter-admin %(ver)s\n'                \
              'Interactive Backport administration console.\n'       \
              'Copyright (c) 2007 Free Ekanayaka\n\n'                                    \
              "Type:  '?' or 'help' for help on commands.\n" %  \
              {'ver':backporter.__version__}
        self.cmdloop()

    ##
    ## Workspace methods
    ##

    def ws_set(self, wsname, ws=None):
        self.wsname = wsname
        self.prompt = "Backporter [%s]> " % self.wsname
        if ws is not None:
            self.__ws = ws

    def ws_open(self):
        try:
            if not self.__ws:
                self.__ws = Workspace(self.wsname)
            return self.__ws
        except Exception, e:
            print 'Failed to open wsironment.', e
            traceback.print_exc()
            sys.exit(1)
    ##
    ## Utility methods
    ##

    def arg_tokenize (self, argstr):
        """`argstr` is an `unicode` string

        ... but shlex is not unicode friendly.
        """
        return [unicode(token, 'utf-8')
                for token in shlex.split(argstr.encode('utf-8'))] or ['']

    def print_listing(self, headers, data, sep=' ', decor=True):
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
    def print_doc(cls, docs, stream=None):
        if stream is None:
            stream = sys.stdout
        if not docs: return
        for cmd, doc in docs:
            print>>stream, cmd
            print>>stream, '\t-- %s\n' % doc
    print_doc = classmethod(print_doc)

    ##
    ## Available Commands
    ##

    ## Help
    _help_help = [('help', 'Show documentation')]

    def all_docs(cls):
        return (cls._help_about + cls._help_help +
                cls._help_initws + cls._help_suite + cls._help_backport)
    all_docs = classmethod(all_docs)

    def do_help(self, line=None):
        arg = self.arg_tokenize(line)
        if arg[0]:
            try:
                doc = getattr(self, "_help_" + arg[0])
                self.print_doc(doc)
            except AttributeError:
                print "No documentation found for '%s'" % arg[0]
        else:
            print 'backporter-admin - The Backporter Administration Console %s' \
                  % backporter.__version__
            if not self.interactive:
                print
                print "Usage: backporter-admin </path/to/workspace> [command [subcommand] [option ...]]\n"
                print "Invoking backporter-admin without command starts "\
                      "interactive mode."
            self.print_doc(self.all_docs())

    
    ## About / Version
    _help_about = [('about', 'Shows information about backporter-admin')]

    def do_about(self, line):
        print
        print 'Backporter Admin Console %s' % backporter.__version__
        print '================================================================='
        print self.license


    ## Quit / EOF
    _help_quit = [['quit', 'Exit the program']]
    _help_exit = _help_quit
    _help_EOF = _help_quit

    def do_quit(self, line):
        print
        sys.exit()

    do_exit = do_quit # Alias
    do_EOF = do_quit # Alias


    ## Workspace
    _help_create = [('create', 'Create and initialize a new workspace')]

    def do_create(self, line):

        if os.path.exists(self.wsname) and os.listdir(self.wsname):
            print "Create for '%s' failed." % self.wsname
            print "Directory exists and is not empty."
            return 2

        arg = self.arg_tokenize(line)

        try:
            try:
                self.__ws = Workspace(self.wsname, create=True)

            except Exception, e:
                print 'Failed to create workspace.', e
                traceback.print_exc()
                sys.exit(1)

        except Exception, e:
            print 'Failed to initialize workspace.', e
            traceback.print_exc()
            return 2

    ## Build
    _help_build = [('build'), ('build', 'Build scheduled packages')]

    def do_build(self, line):
        ws = self.ws_open()
        for s in Suite.select(ws, SuiteType.Released.Value):
            b = Builder(s)
            b.build()

    ## Update
    _help_update = [('update'), ('update', 'Update package status')]

    def do_update(self, line):
        ws = self.ws_open()
        ws.update()

    ## Suite
    _help_suite = [('suite list', 'Show suites'), ('suite chroot [<suite>]', 'Creates build chroot'),
                   ('suite update', 'Update APT lists'),
                   ('suite add <name> <type> <url> <components>', 'Add suite')]

    def do_suite(self, line):
        arg = self.arg_tokenize(line)
        if arg[0]  == 'list':
            self._do_suite_list()
        elif arg[0] == 'add' and len(arg) >= 5:
            self._do_suite_add(arg[1], arg[2], arg[3], " ".join(arg[4:]))
        elif arg[0] == 'chroot' and len(arg) in [1,2]:
            if len(arg) == 1:
                self._do_suite_chroot()
            else:
                self._do_suite_chroot(arg[1])
        elif arg[0]  == 'update':
            self._do_suite_update()
        else:
            self.do_help('suite')

    def _do_suite_list(self):
        data = []

        for s in Suite.select(self.ws_open()):
            data.append((s.name, SuiteType[s.type], s.url, s.comp))
        self.print_listing(['Name', 'Type', 'Url','Components'], data)

    def _do_suite_add(self, name, type, url, comp):
        suite = Suite(self.ws_open())
        suite.name = name
        suite.type = SuiteType.Bleeding.Value
        suite.url  = url
        suite.comp = comp
        suite.insert()

    ## Package
    _help_package = [('package list', 'Show packages'),
                       ('package add <pkg>', 'Add package'),
                       ('package remove <pkg>', 'Remove package')]


    def do_package(self, line):
        arg = self.arg_tokenize(line)
        if arg[0]  == 'list':
            self._do_package_list()
        elif arg[0] == 'add' and len(arg) == 2:
            self._do_package_add(arg[1])
        elif arg[0] == 'remove' and len(arg) == 2:
            self._do_package_remove(arg[1])
        else:
            self.do_help('package')

    def _do_package_list(self):
        data = []
        for p in Package.select(self.ws_open()):
            data.append((p.name, PackageStatus[p.status]))
        self.print_listing(['Name', 'Status'], data)

    def _do_package_add(self, name):
        package = Package(self.ws_open())
        package.name = name
        package.insert()

    def _do_package_remove(self, name):
        package = Package(self.ws_open(), name)
        package.delete()

    ## Test
    _help_test = [('test', 'Tetst')]

    def do_test(self, line):
        for p in Package.select(self.ws_open()):
            
            print p.name, p._get_bleeding()

def run(args):
    """Main entry point."""
    admin = BackporterAdmin()
    if len(args) > 0:
        if args[0] in ('-h', '--help', 'help'):
            return admin.onecmd("help")
        elif args[0] in ('-v','--version','about'):
            return admin.onecmd("about")
        else:
            admin.ws_set(os.path.abspath(args[0]))
            if len(args) > 1:
                s_args = ' '.join(["'%s'" % c for c in args[2:]])
                command = args[1] + ' ' +s_args
                return admin.onecmd(command)
            else:
                while True:
                    admin.run()
    else:
        return admin.onecmd("help")


if __name__ == '__main__':
    run(sys.argv[1:])
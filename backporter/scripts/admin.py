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
# from trac import perm, util, db_default
# from trac.config import default_dir
# from trac.core import TracError
from backporter.ws import Workspace
# from trac.perm import PermissionSystem
from backporter.backport import *
from backporter.suite import *
# from trac.util.html import html
# from trac.util.text import to_unicode, wrap
# from trac.wiki import WikiPage
# from trac.wiki.macros import WikiMacroBase

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
        cmd.Cmd.onecmd(self, line)
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
    _help_about = [('about', 'Shows information about trac-admin')]

    def do_about(self, line):
        print
        print 'Trac Admin Console %s' % trac.__version__
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


    ## Initws
    _help_initws = [('initws <repospath>',
                      'Create and initialize a new workspace')]

    def do_initws(self, line):

        if os.path.exists(self.wsname) and os.listdir(self.wsname):
            print "Initws for '%s' failed." % self.wsname
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

    ## Backport
    _help_suite = [('suite list', 'Show suites'),
                   ('suite add <name> <type> <url> <components>', 'Add suite')]

    def do_suite(self, line):
        arg = self.arg_tokenize(line)
        if arg[0]  == 'list':
            self._do_suite_list()
        elif arg[0] == 'add' and len(arg) >= 5:
            self._do_suite_add(arg[1], arg[2], arg[3], " ".join(arg[4:]))
            if len(arg) == 3:
                self._do_suite_time(arg[1], arg[2])
        else:
            self.do_help('suite')

    def _do_suite_list(self):
        data = []

        for b in Suite.select(self.ws_open()):
            data.append((b.name, SuiteType[b.type], b.url, b.comp))
        self.print_listing(['Name', 'Type', 'Url','Components'], data)

    def _do_suite_add(self, name, type, url, comp):
        suite = Suite(self.ws_open())
        suite.name = name
        suite.type = type
        suite.url  = url
        suite.comp = comp
        suite.insert()

    ## Backport
    _help_backport = [('backport list', 'Show backports'),
                       ('backport add <pkg>', 'Add backport'),
                       ('backport remove <pkg>', 'Remove backport')]

    def do_backport(self, line):
        arg = self.arg_tokenize(line)
        if arg[0]  == 'list':
            self._do_backport_list()
        elif arg[0] == 'add' and len(arg) in [2,3]:
            self._do_backport_add(arg[1])
            if len(arg) == 3:
                self._do_backport_time(arg[1], arg[2])
        elif arg[0] == 'remove' and len(arg) == 2:
            self._do_backport_remove(arg[1])
        else:
            self.do_help('backport')

    def _do_backport_list(self):
        data = []
        ws = self.ws_open()
        print ws.get_db_cnx()
        return
        con = ws.get_db_cnx()
        cur = con.cursor()
        cur.execute("drop table suite")
        cur.execute("create table suite(name text, type integer, url text, comp text)")
        cur.execute("insert into suite values('sid',0,'http://ftp.debian.org/debian','main contrib non-free')")
        cur.execute("insert into suite values('etch',1,'http://ftp.debian.org/debian','main contrib non-free')")
        cur.execute("select * from suite")
        print cur.fetchall()
        con.commit()
#        print row[0]
#        for (suite, type) in cur:
#            print 'suite %s is %d.' % (suite, type)
        return

        for b in Backport.select(self.ws_open()):
            data.append(b.name)
        self.print_listing(['Name', 'Time'], data)

    def _do_backport_add(self, name):
        backport = Backport(self.env_open())
        backport.name = name
        backport.insert()

    def _do_backport_remove(self, name):
        backport = Backport(self.env_open(), name)
        backport.delete()


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

#!/usr/bin/env python

import cmd
from backporter.Backporter import *

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
        cmd.Cmd.onecmd(self,line)

    ##
    ## Available Commands
    ##
    _help_help = [('help', 'Show documentation')]

    ##  Help
    def help_help(self,line):
        print self.doc_header
        print

        for name in self.get_names():
            if not name[0:3] == 'do_':
                continue
            if name in ['do_EOF', 'do_help']:
                continue
            print "   %s" % name[3:]

    def do_help(self, line):
        arg = self._tokenize(line)
        for help in getattr(self, "_help_" + arg[0]):
            self._print_help(help)

    ## Suite
    _help_suite_add = ('suite add <name> <type> <url> <comp>', 'Add suite')
    _help_suite_remove = ('suite remove <name>', 'Remove suite')
    _help_suite = [('suite list', 'Show suites'),
                   ('suite chroot [<name>]', 'Creates build chroot'),
                   _help_suite_remove,
                   _help_suite_add]

    def do_suite(self, line):
        arg = self._tokenize(line)
        if len(arg) == 0:
            return self.do_help('suite')
#try:
        return getattr(self, "_do_suite_" + arg[0])(arg[1:])
#        except AttributeError, e:
#            return self.do_help('suite')            

    def _do_suite_add(self, arg):

        if not len(arg) >= 4:
            return self._print_help(self._help_suite_add)

        Backporter().suite_add(arg[0], arg[1], arg[2], " ".join(arg[3:]))

    def _do_suite_remove(self, arg):

        if not len(arg) == 1:
            return self._print_help(self._help_suite_add)

        Backporter().suite_remove(arg[0])

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

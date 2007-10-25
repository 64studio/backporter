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

    ## Dist
    _help_dist_add = ('dist add <name> <type> <url> <comp>', 'Add dist')
    _help_dist_remove = ('dist remove <name>', 'Remove dist')
    _help_dist = [('dist list', 'Show dists'),
                   ('dist chroot [<name>]', 'Creates build chroot'),
                   _help_dist_remove,
                   _help_dist_add]

    def do_dist(self, line):
        arg = self._tokenize(line)
        if len(arg) == 0:
            return self.do_help('dist')
#try:
        return getattr(self, "_do_dist_" + arg[0])(arg[1:])
#        except AttributeError, e:
#            return self.do_help('dist')            

    def _do_dist_add(self, arg):

        if not len(arg) >= 4:
            return self._print_help(self._help_dist_add)

        Backporter().dist_add(arg[0], arg[1], arg[2], " ".join(arg[3:]))

    def _do_dist_remove(self, arg):

        if not len(arg) == 1:
            return self._print_help(self._help_dist_add)

        Backporter().dist_remove(arg[0])

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

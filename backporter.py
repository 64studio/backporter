#!/usr/bin/env python2.6

__author__ = 'Free Ekanayaka <free@64studio.com>'
__copyright__ = 'Copyright (c) 2007 Free Ekanayaka'
__license__ = """
 Copyright (c) 2007 Free Ekanayaka
 All rights reserved.

 This software is licensed as described in the file COPYING, which
 you should have received as part of this distribution. The terms
 are also available at http://trac.edgewall.org/wiki/TracLicense.

 This software consists of voluntary contributions made by many
 individuals. For the exact contribution history, see the revision
 history and logs, available at http://trac.edgewall.org/log/."""

import sys

from backporter.Shell import Shell

def main(args):

    if len(args) == 1:
        return Shell().cmdloop()

    if len(args) > 1:
        return Shell().onecmd(' '.join(args[1:]))
 
if __name__ == '__main__':
    sys.exit(main(sys.argv))

# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

from pysqlite2.dbapi2 import IntegrityError

class BackporterError(Exception):
    """Exception base class for errors in Trac."""

    def __init__(self, message, title=None, show_traceback=False):
        Exception.__init__(self, message)
        self.message = message
        self.title = title
        self.show_traceback = show_traceback

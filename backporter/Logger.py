# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

import sys

class Logger(object):

    _instance = None 

    def __new__(cls, *args, **kwargs):  
        if cls._instance is None:  
           cls._instance = object.__new__(cls)  
           cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self):
        return

    def debug(self,text):
        if False:
            print 'D: %s' % text

    def fatal(self,text):
        print 'E: %s' % text
        sys.exit(1)

    def info(self,text):
        print 'I: %s' % text

    def warn(self,text):
        print 'W: %s' % text

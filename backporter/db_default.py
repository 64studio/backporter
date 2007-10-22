# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Ekanayaka Free
# All rights reserved.
#

from backporter.db import Table, Column, Index
from backporter.suite import SuiteType

##
## Database schema
##

schema = [
    # Common
    Table('suite', key='name')[
        Column('name'),
        Column('type', type='int'),
        Column('url'),
        Column('comp')],
    Table('package', key=('name'))[
        Column('name'),
        Column('status', type='int')],
    Table('version', key=('package', 'suite'))[
        Column('package'),
        Column('suite'),
        Column('value')],
    Table('build', key=('package', 'suite', 'arch','action'))[
        Column('package'),
        Column('suite'),
        Column('arch'),
        Column('action')],
    Table('enum', key=('type', 'name'))[
        Column('type'),
        Column('name'),
        Column('value')],
]

url = {'debian':'http://ftp.debian.org/debian'}

data = (('suite',
         ('name','type','url','comp'),
         (('etch',SuiteType.Released.Value,url['debian'],'main contrib non-free'),
          ('sid' ,SuiteType.Bleeding.Value,url['debian'],'main contrib non-free'))),
        ('enum',
         ('type', 'name', 'value'),
         (('status', 'new', 1),('status', 'old', 0)))
        )

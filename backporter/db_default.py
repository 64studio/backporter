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
    Table('backport', key=('package'))[
        Column('package'),
        Column('status', type='int')],
    Table('version', key=('package', 'suite'))[
        Column('package'),
        Column('suite'),
        Column('version'),
        Column('time', type='int')],
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

data = (('suite',
         ('name','type','url','comp'),
         (('etch',SuiteType.Released.Value,'http://','main'),
          ('sid',SuiteType.Bleeding.Value,'http://','main'))),
        ('enum',
         ('type', 'name', 'value'),
         (('status', 'new', 1),('status', 'old', 0)))
        )

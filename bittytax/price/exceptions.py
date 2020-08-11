# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import os

from ..config import config
from .datasource import DataSourceBase

class UnexpectedDataSourceError(Exception):
    def __init__(self, value):
        super(UnexpectedDataSourceError, self).__init__()
        self.value = value

    def __str__(self):
        return "Invalid data source: \'%s\' in %s, use {%s}" % (
            self.value,
            os.path.join(config.BITTYTAX_PATH, config.BITTYTAX_CONFIG),
            ','.join([ds.__name__ for ds in DataSourceBase.__subclasses__()]))

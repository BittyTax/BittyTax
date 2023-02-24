# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import os

from ..config import config


class DataSourceError(Exception):
    def __init__(self, data_source, value=None):
        super(DataSourceError, self).__init__()
        self.data_source = data_source
        self.value = value


class UnexpectedDataSourceError(DataSourceError):
    def __str__(self):
        return "Invalid data source: '%s' in %s, use {%s}" % (
            self.data_source,
            os.path.join(config.BITTYTAX_PATH, config.BITTYTAX_CONFIG),
            ",".join([ds.__name__ for ds in self.value.__subclasses__()]),
        )


class UnexpectedDataSourceAssetIdError(DataSourceError):
    def __str__(self):
        return "Invalid data source asset ID: '%s' for '%s' in %s" % (
            self.data_source,
            self.value,
            os.path.join(config.BITTYTAX_PATH, config.BITTYTAX_CONFIG),
        )

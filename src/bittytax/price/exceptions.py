# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import os

from ..config import config
from ..constants import BITTYTAX_PATH


class DataSourceError(Exception):
    def __init__(self, data_source, value=None):
        super().__init__()
        self.data_source = data_source
        self.value = value


class UnexpectedDataSourceError(DataSourceError):
    def __str__(self):
        return (
            f"Invalid data source: '{self.data_source}' in "
            f"{os.path.join(BITTYTAX_PATH, config.BITTYTAX_CONFIG)}, use "
            f"{{{','.join([ds.__name__ for ds in self.value.__subclasses__()])}}}"
        )


class UnexpectedDataSourceAssetIdError(DataSourceError):
    def __str__(self):
        return (
            f"Invalid data source asset ID: '{self.data_source}' for '{self.value}' in "
            f"{os.path.join(BITTYTAX_PATH, config.BITTYTAX_CONFIG)}"
        )

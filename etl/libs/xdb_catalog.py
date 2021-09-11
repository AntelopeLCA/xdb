"""
An LcCatalog subclass that yields XdbQueries
"""

from antelope_core import StaticCatalog
from .xdb_query import XdbQuery
from .meter_reader import MeterReader

class XdbCatalog(StaticCatalog):
    def __init__(self, *args, **kwargs):
        super(XdbCatalog, self).__init__(*args, **kwargs)
        self.meter = MeterReader()

    _query_type = XdbQuery

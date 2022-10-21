"""
A CatalogQuery subclass that enforces access limitations
"""

from antelope_core.catalog_query import CatalogQuery
from antelope.interfaces.iexchange import EXCHANGE_VALUES_REQUIRED
from antelope.interfaces.ibackground import BACKGROUND_VALUES_REQUIRED


_VALUES_REQUIRED = EXCHANGE_VALUES_REQUIRED.union(BACKGROUND_VALUES_REQUIRED)
_NOAUTH_IFACES = ('basic', 'index')

_AUTH_NOT_REQUIRED = {'is_lcia_engine'}


class InterfaceNotAuthorized(Exception):
    pass


class XdbQuery(CatalogQuery):
    def __init__(self, origin, catalog=None, grants=(), **kwargs):
        super(XdbQuery, self).__init__(origin, catalog=catalog, **kwargs)
        self._grants = {g.access: g for g in grants if origin.startswith(g.origin)}  # we only store one grant per iface. so don't give us more.

    def authorized_interfaces(self):
        return set(self._grants.keys())

    def _perform_query(self, itype, attrname, exc, *args, strict=False, **kwargs):
        if attrname not in _AUTH_NOT_REQUIRED:
            if itype in self._grants:
                grant = self._grants[itype]
                if attrname in _VALUES_REQUIRED:
                    self._catalog.meter.values(grant)
                else:
                    self._catalog.meter.access(grant)

            else:
                if itype not in _NOAUTH_IFACES:
                    raise InterfaceNotAuthorized(self.origin, itype)
                # otherwise pass

        return super(XdbQuery, self)._perform_query(itype, attrname, exc, *args, strict=strict, **kwargs)

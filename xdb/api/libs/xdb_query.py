"""
A CatalogQuery subclass that enforces access limitations
"""

from antelope_core.catalog_query import CatalogQuery, BackgroundSetup
from antelope.interfaces.iexchange import EXCHANGE_VALUES_REQUIRED
from antelope.interfaces.ibackground import BACKGROUND_VALUES_REQUIRED
from antelope.models import OriginMeta


_VALUES_REQUIRED = EXCHANGE_VALUES_REQUIRED.union(BACKGROUND_VALUES_REQUIRED)
_NOAUTH_IFACES = ('basic', 'index')

_AUTH_NOT_REQUIRED = {'is_lcia_engine', 'check_bg'}


class InterfaceNotAuthorized(Exception):
    pass


class XdbQuery(CatalogQuery):
    def __init__(self, origin, catalog=None, grants=(), **kwargs):
        super(XdbQuery, self).__init__(origin, catalog=catalog, **kwargs)
        # we have two different grants listings-- one, the grants for *this* origin
        # (note that a grant authorizes more-specific, but not less-specific, origins)
        # so if MY origin starts with the grant origin, then MY origin is authorized
        self._grants = {g.access: g for g in grants if origin.startswith(g.origin)}  # we only store one grant per iface. so don't give us more.
        # two, we have all the grants
        self._all_grants = tuple(grants)

    def authorized_interfaces(self):
        return set(self._grants.keys())

    def origin_meta(self, origin):
        gs = [g for g in self._all_grants if g.origin == origin]
        if len(gs) == 0:
            raise KeyError(origin)
        is_lcia = any(g.origin == 'local.qdb' for g in self._all_grants)
        return OriginMeta(origin=origin, is_lcia_engine=is_lcia, interfaces=sorted(set(g.access for g in gs)))

    def authorized_origins(self):
        for org in sorted(set(g.origin for g in self._all_grants)):
            yield org

    def _setup_background(self, bi):
        """
        need to provide an ordinary non-metering catalog query to the background
        :param bi:
        :return:
        """
        self._debug('Setting up non-metering background interface')
        try:
            bi.setup_bm(CatalogQuery(self._origin, self._catalog))
        except AttributeError:
            raise BackgroundSetup('Failed to configure background')

    def _perform_query(self, itype, attrname, exc, *args, **kwargs):
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

        return super(XdbQuery, self)._perform_query(itype, attrname, exc, *args, **kwargs)

"""
A CatalogQuery subclass that enforces access limitations
"""

from antelope_core.catalog_query import CatalogQuery, BackgroundSetup
from antelope.interfaces.iexchange import EXCHANGE_VALUES_REQUIRED
from antelope.interfaces.ibackground import BACKGROUND_VALUES_REQUIRED
from antelope.models import OriginMeta

from requests import session, HTTPError
import json
import os
import logging


bbhost = os.environ.get('BLACKBOOK_HOST', None)
protocol = os.environ.get('BLACKBOOK_PROTOCOL', 'http')


_VALUES_REQUIRED = EXCHANGE_VALUES_REQUIRED | BACKGROUND_VALUES_REQUIRED
_NOAUTH_IFACES = ('basic', 'index')

_AUTH_NOT_REQUIRED = {'is_lcia_engine', 'check_bg'}


class InterfaceNotAuthorized(Exception):
    pass


class GuestTokenFailed(Exception):
    """
    some server-side failure
    """
    pass


class GuestTokenRejected(Exception):
    """
    quota exceeded
    """
    pass


class XdbQuery(CatalogQuery):
    def __init__(self, origin, catalog=None, grants=(), token=None, tid='', **kwargs):
        super(XdbQuery, self).__init__(origin, catalog=catalog, **kwargs)
        # we have two different grants listings-- one, the grants for *this* origin
        # (note that a grant authorizes more-specific, but not less-specific, origins)
        # so if MY origin starts with the grant origin, then MY origin is authorized
        self._grants = {g.access: g for g in grants if origin.startswith(g.origin)}  # we only store one grant per iface. so don't give us more.
        # two, we have all the grants
        self._all_grants = tuple(grants)
        self._token = token
        self._tid = str(tid)

    def authorized_interfaces(self):
        return set(self._grants.keys())

    @property
    def user(self):
        if len(self._all_grants) > 0:
            return self._all_grants[0].user
        return None

    @property
    def guest(self):
        if self._tid.find('guest') >= 0:
            return True
        return False

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

    def check_guest_token(self, iface, route):
        if iface in _NOAUTH_IFACES:
            return True
        with session() as s:
            s.headers['Authorization'] = 'bearer %s' % self._token
            logging.info('Testing guest token against %s' % bbhost)
            try:
                resp = s.get('%s://%s/check_guest/%s/%s' % (protocol, bbhost, iface, route))
            except HTTPError as e:
                raise GuestTokenFailed(*e.args)
            j = json.loads(resp.content)
            return bool(j)

    def _perform_query(self, itype, attrname, exc, *args, **kwargs):
        if attrname not in _AUTH_NOT_REQUIRED:
            if self.guest:
                if not self.check_guest_token(itype, attrname):
                    raise GuestTokenRejected(itype, attrname)

            if itype in self._grants:
                grant = self._grants[itype]
                if attrname in _VALUES_REQUIRED:
                    self._catalog.meter.values(grant)
                else:
                    self._catalog.meter.access(grant)

            else:
                if itype not in _NOAUTH_IFACES:
                    raise InterfaceNotAuthorized(self.origin, itype, attrname)
                # otherwise pass

        return super(XdbQuery, self)._perform_query(itype, attrname, exc, *args, **kwargs)

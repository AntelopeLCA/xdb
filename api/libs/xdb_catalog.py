"""
An LcCatalog subclass that yields XdbQueries
"""

from antelope.xdb_tokens import IssuerKey
from antelope_core import LcCatalog
from .xdb_query import XdbQuery
from .meter_reader import MeterReader

import os
import json
import requests
import datetime


PUBKEYS_FILENAME = 'PUBKEYS.json'


class XdbCatalog(LcCatalog):

    pubkeys = None

    @property
    def pubkeys_file(self):
        return os.path.join(self._rootdir, PUBKEYS_FILENAME)

    def load_pubkeys(self):

        if not os.path.exists(self.pubkeys_file):
            self.pubkeys = dict()

        else:
            with open(self.pubkeys_file, 'r') as fp:
                _pubkeys = [IssuerKey(**d) for d in json.load(fp)]

            self.pubkeys = {k.issuer: k for k in _pubkeys}

    def save_pubkeys(self):
        # in lieu of a persistence layer
        j = [k.dict() for k in self.pubkeys.values()]
        with open(self.pubkeys_file, 'w') as zp:
            json.dump(j, zp)

    def retrieve_trusted_issuer_key(self, host='localhost:80', protocol='http'):
        """
        A utility file to pre-seed the xdb PUBKEYS path with a master_issuer public key from a trusted host.
        Obviously the grown-ups have more sophisticated ways to manage public keys.
        :param host:
        :param path:
        :param protocol:
        :return:
        """
        with requests.session() as s:
            resp = s.get('%s://%s/master_issuer' % (protocol, host))
        j = json.loads(resp.content)
        if isinstance(j['expiry'], str):
            j['expiry'] = datetime.datetime.fromisoformat(j['expiry']).timestamp()
        master_issuer = IssuerKey(**j)
        self.pubkeys[master_issuer.issuer] = master_issuer
        self.save_pubkeys()

    def reset_origin(self, origin):
        for res in self.resources(origin):
            self.delete_resource(res)
        self._queries.pop(origin, None)

    def __init__(self, *args, **kwargs):
        super(XdbCatalog, self).__init__(*args, **kwargs)
        self.meter = MeterReader()
        self.load_pubkeys()

    _query_type = XdbQuery

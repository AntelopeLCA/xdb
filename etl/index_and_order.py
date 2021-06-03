"""

Given an exchange resource on aws-data, build and deploy index and background resources

The steps here are:

 - we assume the specified origin is already synced from aws.
 - we auto-generate an index filename and test to see if it is present
 - if not,
    - we unzip the 7z if it's a 7z
    - we create the index and write the config
 - then we check the same auto-generated background name
 - if not, create background
 - I don't think this needs to be a class
"""
import os
import hashlib
import json

from patoolib import extract_archive
import tempfile
import magic

from antelope import BasicQuery
from antelope_core.lc_resource import LcResource
from antelope_background import TarjanBackground
from .file_accessor import AwsFileAccessor


def _hash_file(source):
    """
    Computes the hash of a source file, for use in naming derived index and ordering files
    :param source:
    :return:
    """
    with open(source, 'rb') as fp:
        h = hashlib.sha1(fp.read())

    return h.hexdigest()


def is_7z(filename):
    return magic.from_file(os.path.realpath(filename)).startswith('7-zip archive')


class StandAloneQuery(BasicQuery):
    def __init__(self, exch, index, **kwargs):
        super(StandAloneQuery, self).__init__(exch, **kwargs)
        self._index = index

    def _perform_query(self, itype, attrname, exc, *args, strict=False, **kwargs):
        if itype == 'index':
            iface = self._index.make_interface(itype)
            return getattr(iface, attrname)(*args, **kwargs)
        else:
            return super(StandAloneQuery, self)._perform_query(itype, attrname, exc, *args, strict=strict, **kwargs)


class AwsIndexAndOrder(AwsFileAccessor):
    def _target_index(self, origin, s_hash):
        return os.path.join(self._path, origin, 'index', 'json', s_hash + '.json.gz')

    def _target_background(self, origin, s_hash):
        return os.path.join(self._path, origin, 'background', 'TarjanBackground', s_hash + '.mat')

    @staticmethod
    def write_index_config(index_file, hints=None):
        index_config = os.path.join(os.path.dirname(index_file), 'config.json')
        if hints is None:
            config = dict()
        else:
            config = {'hints': sorted([list(g) for g in hints], key=lambda x: x[0])}
        ix_cfg = {
            '_internal': True,
            'static': True,
            'config': config
        }
        with open(index_config, 'w') as fp:
            json.dump(ix_cfg, fp, indent=2)

    def _index_and_order_res(self, res, tgt_ix, tgt_bg):
        res.check(None)

        # create index
        if os.path.exists(tgt_ix):
            index = self.create_resource(tgt_ix)
        else:
            index = res.make_index(tgt_ix)
            self.write_index_config(tgt_ix, hints=res.config['hints'])

        saq = StandAloneQuery(res.archive, index)

        if not os.path.exists(tgt_bg):
            os.makedirs(os.path.dirname(tgt_bg), exist_ok=True)
            bg = TarjanBackground(tgt_bg, save_after=True)
            bg.create_flat_background(saq)

    def run_origin(self, origin):
        if origin in self._origins:
            for source in self.gen_sources(origin, 'exchange'):
                s_hash = _hash_file(source)
                tgt_ix = self._target_index(origin, s_hash)
                tgt_bg = self._target_background(origin, s_hash)
                if os.path.exists(tgt_ix) and os.path.exists(tgt_bg):
                    continue
                # at least one is missing- so we need to instantiate the resource

                deflt_res = self.create_resource(source)
                if is_7z(source):
                    with tempfile.TemporaryDirectory() as dirpath:
                        extract_archive(source, outdir=dirpath)

                        cfg = self.get_config(source)
                        res = LcResource(origin, dirpath, deflt_res.ds_type, interfaces='exchange', **cfg)
                        self._index_and_order_res(res, tgt_ix, tgt_bg)
                else:
                    self._index_and_order_res(deflt_res, tgt_ix, tgt_bg)

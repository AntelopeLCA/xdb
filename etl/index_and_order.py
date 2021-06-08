"""

Given an exchange resource on aws-data, build and deploy index and background resources.  The IndexAndOrder class
is meant to be run INTERACTIVELY, and the product of the interaction is a set of operable configuration files.

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
from antelope_core.archives import InterfaceError, CheckTerms


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
    return magic.from_file(os.path.realpath(filename)).startswith('7-zip archive')  # this is not necessary, is it?


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

    def check_terms(self):
        """
        We want to inspect the archive's exchanges

        :return:
        """
        return CheckTerms(self)


class IndexAndOrder(object):

    @property
    def _tgt_ix(self):
        return os.path.join(self._fa.path, self.origin, 'index', 'json', self._s_hash + '.json.gz')

    @property
    def _tgt_bg(self):
        return os.path.join(self._fa.path, self.origin, 'background', 'TarjanBackground', self._s_hash + '.mat')

    def __init__(self, file_accessor, origin, source):
        self._fa = file_accessor
        if origin not in self._fa.origins:
            raise ValueError("origin %s not known" % origin)

        self._origin = origin
        self._source = source
        self._saq = None
        self._i_res = None
        self._b_res = None

        self._s_hash = _hash_file(source)
        self._e_res = self._fa.create_resource(source)

        if self._check_ix() and self._check_bg():
            return

        # at least one is missing- so we need to instantiate the resource

    def run(self):
        if is_7z(self._source):
            with tempfile.TemporaryDirectory() as dirpath:
                extract_archive(self._source, outdir=dirpath)

                cfg = self._fa.read_config(self._source)
                res = LcResource(self.origin, dirpath, self._e_res.ds_type, interfaces='exchange', **cfg)
                self.index_res(res)
                self._e_res.check(None)

                self.order_res()

        else:
            self.index_res(self._e_res)
            self.order_res()

    @property
    def origin(self):
        return self._origin

    @property
    def query(self):
        return self._saq

    def check_bg(self, **kwargs):
        self._b_res.check_bg(**kwargs)

    def write_config(self, **kwargs):
        cfg = os.path.join(os.path.dirname(self._e_res.source), 'config.json')
        ex_cfg = {
            'config': self._e_res.export_config()
        }
        ex_cfg.update(**kwargs)
        with open(cfg, 'w') as fp:
            json.dump(ex_cfg, fp, indent=2)
        if self._i_res:
            self.write_index_config()  # deliberately omit kwargs

    def write_index_config(self, **kwargs):
        # update the local resource
        self._i_res.config['hints'] = self._e_res.config['hints']
        self._i_res.init_args.update(**kwargs)
        ix_cfg = self._i_res.serialize(stripped=True)
        # write the updates to file
        index_config = os.path.join(os.path.dirname(self._tgt_ix), 'config.json')
        with open(index_config, 'w') as fp:
            json.dump(ix_cfg, fp, indent=2)

    def index_res(self, res=None):
        if res is None:
            res = self._e_res
        res.check(None)

        if self._i_res is None:
            # create index
            index = res.make_index(self._tgt_ix)  # returns an archive
            self._i_res = LcResource.from_archive(index, ('basic', 'index'), source=self._tgt_ix)
            self._i_res.check(None)
            self.write_index_config()

        self._saq = StandAloneQuery(res.archive, self._i_res.archive)

    def order_res(self):

        if self._b_res is None:
            os.makedirs(os.path.dirname(self._tgt_bg), exist_ok=True)
            bg = TarjanBackground(self._tgt_bg, save_after=True)
            bc = bg.make_interface('configure')
            bc.apply_config(self._e_res.config)  # only prefer_provider will get applied

            bg.create_flat_background(self._saq)
            self._b_res = LcResource.from_archive(bg, 'background', source=self._tgt_bg)
            self._b_res.check(None)

    def _check_ix(self):
        if os.path.exists(self._tgt_ix):
            # load
            self._i_res = self._fa.create_resource(self._tgt_ix)
            self._i_res.check(None)
            return True
        self._i_res = None
        return False

    def _check_bg(self):
        if os.path.exists(self._tgt_bg):
            # load
            self._b_res = self._fa.create_resource(self._tgt_bg)
            self._b_res.check(None)
            return True
        self._b_res = None
        return False

    def _clear_bg(self):
        if os.path.exists(self._tgt_bg):
            os.remove(self._tgt_bg)
        self._b_res = None

    def _clear_ix(self):
        if os.path.exists(self._tgt_ix):
            os.remove(self._tgt_ix)
        self._i_res = None
        self._clear_bg()

    def configure(self, option, *args):
        """
        Add a configuration setting to the resource, and apply it to the archive.
        # note: config is not written until write_config() is called

        :param option: the option being configured
        :param args: the arguments, in the proper sequence
        :return: None if archive doesn't support configuration; False if unsuccessful, True if successful
        """
        try:
            cf = self._e_res.archive.make_interface('configure')
        except InterfaceError:
            print('No Configure interface')
            return None

        if cf.check_config(option, args):
            cf.apply_config({option: {args}})
            self._e_res.config[option].add(args)
            # note: config is not written until write_config() is called

            # others-- e.g. changing references will require the index to be rewritten
            if option in ("set_reference", "unset_reference"):
                self._clear_ix()

            if option in ("preferred_provider", ):
                self._clear_bg()

            return True
        print('Configuration failed validation.')
        return False

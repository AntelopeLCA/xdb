import os
import json
from antelope_core import LcResource


DEFAULT_PRIORITIES = {
    'exchange': 20,
    'index': 50,
    'background': 80
}


class AwsFileAccessor(object):

    def __init__(self, load_path):
        self._path = os.path.abspath(load_path)  # this has the benefits of collapsing '..' and trimming trailing '/'
        self._origins = os.listdir(self._path)

    @property
    def origins(self):
        for k in self._origins:
            yield k

    @staticmethod
    def read_config(source):
        cfg = os.path.join(os.path.dirname(source), 'config.json')
        if os.path.exists(cfg):
            with open(cfg) as fp:
                config = json.load(fp)
        else:
            config = dict()
        return config

    def gen_sources(self, org, iface):
        iface_path = os.path.join(self._path, org, iface)
        if not os.path.exists(iface_path):
            return
        for ds_type in os.listdir(iface_path):
            ds_path = os.path.join(iface_path, ds_type)
            if not os.path.isdir(ds_path):
                continue
            for fn in os.listdir(ds_path):
                if fn == 'config.json':
                    continue
                # if we want to order sources, this is the place to do it
                source = os.path.join(ds_path, fn)
                yield source

    def create_resource(self, source):
        if not source.startswith(self._path):
            raise ValueError('Path not contained within our filespace')
        rel_source = source[len(self._path)+1:]
        org, iface, ds_type, fn = rel_source.split(os.path.sep)  # note os.pathsep is totally different
        cfg = self.read_config(source)
        priority = cfg.pop('priority', DEFAULT_PRIORITIES[iface])
        return LcResource(org, source, ds_type, interfaces=iface, priority=priority, **cfg)

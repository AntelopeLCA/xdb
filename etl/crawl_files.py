import os
import json


class AntelopeFileCrawler(object):

    def __init__(self, cat, load_path):
        self._cat = cat
        self._path = load_path
        self._origins = os.listdir(load_path)

    @property
    def origins(self):
        for k in self._origins:
            yield k

    @staticmethod
    def _get_config(iface_path):
        cfg = os.path.join(iface_path, 'config.json')
        if os.path.exists(cfg):
            with open(cfg) as fp:
                config = json.load(fp)
        else:
            config = dict()
        return config

    def _new_resources(self, org, iface):
        iface_path = os.path.join(self._path, org, iface)
        if not os.path.exists(iface_path):
            return
        config = self._get_config(iface_path)
        priority = config.pop('priority', 50)
        for ds_type in os.listdir(iface_path):
            if ds_type == 'config.json':
                continue
            ds_path = os.path.join(iface_path, ds_type)
            for i, fn in enumerate(os.listdir(ds_path)):
                source = os.path.join(ds_path, fn)
                ds_pri = priority + i
                res = self._cat.new_resource(org, source, ds_type, interfaces=iface, priority=ds_pri, **config)
                res.check(self._cat)

    def _load_origin(self, org):
        """
        First we add exchange resources- the
        :param org:
        :return:
        """
        for iface in ('exchange', 'index', 'background'):
            self._new_resources(org, iface)

    def load_data(self):
        for org in self.origins:
            self._load_origin(org)
            self._cat.query(org).check_bg()

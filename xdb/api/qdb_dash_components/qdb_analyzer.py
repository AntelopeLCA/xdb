import pandas as pd
from itertools import chain


def _cf_to_fff(cf):
    """
    use a cf to generate records for factors_for_flowable

    index: (quantity | context | location | ref unit) value: value series: flowable
    :param cf:
    :return:
    """
    for l in cf.locations:
        yield (cf.quantity.name, cf.context.name, l, cf.ref_quantity.unit), cf.query(l).value


def _cf_to_ffq(cf):
    """
    use a cf to generate records for factors_for_quantity

    index: (flowable | context | location | ref unit) value: value series: quantity | unit
    :param cf:
    :return:
    """
    for l in cf.locations:
        yield (cf.flowable, cf.context.name, l, cf.ref_quantity.unit), cf.query(l).value


class QdbAnalyzer:
    def __init__(self, cat, flowables=None, contexts=None, quantities=None):
        self.cat = cat
        self._fb = list()
        self._cx = list()
        self._q = list()
        if flowables:
            self._fb.extend(self.lcia.get_flowable(f) for f in flowables)
        if contexts:
            self._cx.extend(self.lcia[c] for c in contexts)
        if quantities:
            self._q.extend(self.cat.get_canonical(q) for q in quantities)

    @property
    def flowables(self):
        for fb in self._fb:
            yield fb

    @property
    def contexts(self):
        for cx in self._cx:
            yield cx

    @property
    def quantities(self):
        for q in self._q:
            yield q

    @property
    def lcia(self):
        return self.cat.lcia_engine

    def _pass_cf(self, cf):
        """

        :param cf:
        :return:
        """
        fb = self.lcia.get_flowable(cf.flowable)
        return (len(self._cx) == 0 or cf.context in self._cx) and \
            (len(self._fb) == 0 or fb in self._fb) and \
            (len(self._q) == 0 or cf.quantity in self._q)

    def _factors_for_flowable(self, flowable):
        return pd.Series(dict(chain(*(_cf_to_fff(cf) for cf in self.lcia.factors_for_flowable(flowable)
                                      if self._pass_cf(cf)))))

    def debug_for_flowables(self):
        return pd.DataFrame({'flowables': ('F1', 'F2', 'F3')})
        # return self._factors_for_flowable(self._fb[0])

    def factors_for_flowables(self):
        """
        columns: flowable
        :return:
        """
        df = pd.DataFrame({
            fb.name: self._factors_for_flowable(fb.name)
            for fb in self.flowables})
        if len(df.index.names) == 4:
            df.rename_axis(['Quantity', 'Context', 'Location', 'Ref Unit'], inplace=True)
        return df.loc[df.sort_values(by=df.columns[0],
                                     ascending=False).notna().sum(axis=1).sort_values(ascending=False).index]

    def _factors_for_quantity(self, quantity):
        return pd.Series(dict(chain(*(_cf_to_ffq(cf) for cf in self.lcia.factors_for_quantity(quantity)
                                      if self._pass_cf(cf)))))

    def factors_for_quantities(self):
        """
        columns: flowable
        :return:
        """
        df = pd.DataFrame({
            (q['Method'], q['Category'], q.unit): self._factors_for_quantity(q)
            for q in self.quantities
        })
        if len(df.index.names) == 4:
            df.rename_axis(['Flowable', 'Context', 'Location', 'Ref Unit'], inplace=True)
        return df.loc[df.sort_values(by=df.columns[0],
                                     ascending=False).notna().sum(axis=1).sort_values(ascending=False).index]

    def analyze(self):
        if len(self._fb) == 0:
            if len(self._q) == 0:
                return pd.DataFrame()
            return self.factors_for_quantities()
        if len(self._q) == 0:
            return self.factors_for_flowables()
        if len(self._q) < len(self._fb):
            return self.factors_for_quantities()
        return self.factors_for_flowables()

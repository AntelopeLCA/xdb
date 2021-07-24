"""
LCIA Operational Models

0. Foreground Characterization (lcia on hand)
User has a foreground with a local catalog
User creates local flow refs in a model
user obtains a qdb address for an LCIA indicator (origin + external ref, or simple UUID)
user POSTS a list of FlowSpec models to /origin/lcia_ref/factors
the LCIA engine returns a list of quantity relation results for the supplied flows, in the format:
flow_id;
[QRResults]
and for each QRresult, the context is the one PASSED, not the canonical one used for lookup.  This ensures that the
client can map its contexts onto the results.  The client can then cache all those scores on its flow refs and
perform its own local LCIA.

0a. Foreground LCIA (lcia on hand)
Client requests an lci from an xdb (which is cached); characterizes the set of flows received via 0; and then
performs local LCIA on the background data

1. Background LCIA aka "spooky action at a distance" (lcia on xdb)
Perfect for EPDs, proprietary data sets, and results reporting
xdb hosts the entity about which the score is desired
client specifies both the entity and the LCIA method by reference, either locally (external ref e.g. uuid) or fully
qualified (also with origin).
xdb generates the LCI and then performs local LCIA (as step 0a above) on its designated qdb.  That qdb has to
recognize the query link, and the query must be authorized to use the qdb. [Note: this has only been achieved with
an integrated qdb, not yet with an 'air gapped' qdb- but presumably it would be equivalent to 0+0a]
The xdb receives the results and can decide what level of detail to return to the user.

2. LCIA of exchanges (lcia on qdb)
User generates a list of exchanges from an LCI or other means, and POSTS the exchanges to the quantity database, which
intakes them and performs the LCIA and returns the results.  Here again the LCIA Details must include FlowSpecs of the
inputs (e.g. context + locale), not the canonical/GLO values, so that the client can map them back to its posted
exchanges.  The locale of the conversion is reported in the QRResult.

"""

from api.models.response import QdbMeta
from .runtime import cat, search_entities, do_lcia
from fastapi import APIRouter, HTTPException
from typing import List, Optional

import re

from antelope import EntityNotFound, UnknownOrigin, CatalogRef, ExchangeRef
from antelope_core.models import Entity, Context, Characterization, DetailedLciaResult, UnallocatedExchange
from antelope_core.entities import MetaQuantityUnit, LcFlow, LcProcess

lcia = cat.lcia_engine

qdb_router = APIRouter(prefix="/qdb")

@qdb_router.get("/", response_model=QdbMeta)
def get_qdb_meta():
    return QdbMeta.from_cat(cat)


@qdb_router.get("/synonyms", response_model=List[str])
def get_synonyms(term: str):
    return lcia.synonyms(term)


def _filter_canonical_quantities(**kwargs):
    name = kwargs.pop('name', None)

    sargs = {k: v for k, v in filter(lambda x: x[1] is not None, kwargs.items())}

    for q in lcia.quantities(search=name):
        for k, v in sargs.items():
            if not q.has_property(k):
                continue
            else:
                if not bool(re.search(v, q[k], flags=re.IGNORECASE)):
                    continue
        yield q


@qdb_router.get("/quantities", response_model=List[Entity])
@qdb_router.get("/flowproperties", response_model=List[Entity])
@qdb_router.get("/flow_properties", response_model=List[Entity])
def search_quantities(name: Optional[str]=None,
                      unit: Optional[str]=None,
                      method: Optional[str]=None,
                      category: Optional[str]=None,
                      indicator: Optional[str]=None):
    kwargs = {'name': name,
              'referenceunit': unit,
              'method': method,
              'category': category,
              'indicator': indicator}
    return list(Entity.from_entity(k) for k in _filter_canonical_quantities(**kwargs))


@qdb_router.get("/lcia_methods", response_model=List[Entity])
@qdb_router.get("/lciamethods", response_model=List[Entity])
def search_lcia_methods(name: Optional[str]=None,
                      unit: Optional[str]=None,
                      method: Optional[str]=None,
                      category: Optional[str]=None,
                      indicator: Optional[str]=None):
    kwargs = {'name': name,
              'referenceunit': unit,
              'method': method,
              'category': category,
              'indicator': indicator}

    return list(Entity.from_entity(k) for k in filter(lambda x: x.is_lcia_method,
                                                      _filter_canonical_quantities(**kwargs)))


@qdb_router.get("/lcia", response_model=List[Entity])
def get_meta_quantities(name: Optional[str] = None,
                        method: Optional[str] = None):
    kwargs = {'name': name,
              'method': method}
    query = cat.query('local.qdb')
    return list(search_entities(query, 'quantities', unit=MetaQuantityUnit.unitstring, **kwargs))


@qdb_router.get("/contexts", response_model=List[Context])
def get_contexts(elementary: bool=None, sense=None, parent=None):
    if parent is not None:
        parent = lcia[parent]
    cxs = [Context.from_context(cx) for cx in lcia.contexts()]
    if elementary is not None:
        cxs = filter(lambda x: x.elementary == elementary, cxs)
    if sense is not None:
        cxs = filter(lambda x: x.sense == sense, cxs)
    if parent is not None:
        cxs = filter(lambda x: x.parent == parent, cxs)
    return list(cxs)


@qdb_router.get("/contexts/{context}", response_model=Context)
def get_contexts(context: str):
    return Context.from_context(lcia[context])


def _get_canonical(origin, quantity):
    try:
        if origin is None:
            q = lcia.get_canonical(quantity)
        else:
            cat.query(origin).get(quantity)  # registers it with qdb
            q = lcia.get_canonical(quantity)
    except EntityNotFound:
        raise HTTPException(404, f"quantity {quantity} not found")
    except UnknownOrigin:
        raise HTTPException(404, f"Unknown origin {origin}")
    return q


@qdb_router.get("/{quantity}/factors", response_model=List[Characterization])
@qdb_router.get("/{origin}/{quantity}/factors", response_model=List[Characterization])
@qdb_router.get("/{quantity}/factors/{flowable}", response_model=List[Characterization])
@qdb_router.get("/{origin}/{quantity}/factors/{flowable}", response_model=List[Characterization])
def factors_for_quantity(quantity: str, origin: str=None, flowable: str=None, context: str=None):
    q = _get_canonical(origin, quantity)
    if context is not None:
        context = lcia[context]
    return [Characterization.from_cf(cf) for cf in lcia.factors_for_quantity(q, flowable=flowable, context=context)]


@qdb_router.get("/{quantity}", response_model=Entity)
@qdb_router.get("/{origin}/{quantity}", response_model=Entity)
@qdb_router.get("/load/{origin}/{quantity}", response_model=Entity)
def load_quantity(quantity: str, origin: str=None):
    q = _get_canonical(origin, quantity)
    ent = Entity.from_entity(q)
    for p in q.properties():
        ent.properties[p] = q[p]
    return ent


def _lcia_exch_ref(p, x):
    """
    This turns a provided inventory exchange into an input argument for LCIA
    at the other end, the
    :param p:
    :param x:
    :return:
    """
    if p.origin is None:
        p.origin = x.origin
    if x.flow.external_ref is not None:
        try:
            flow = cat.get_qdb_entity(x.origin, x.flow.external_ref)
        except KeyError:
            """
            Need to use: external_ref, quantity_ref, flowable, context, locale.
            Need to think about including CAS number (or synonyms) in FlowSpec as optional params
            """
            ref_q = _get_canonical(x.origin, x.flow.quantity_ref)
            flow = CatalogRef.from_query(x.flow.external_ref, cat._qdb.query, 'flow', masquerade=x.origin,
                                         name=x.flow.flowable, reference_entity=ref_q,
                                         context=tuple(x.flow.context), locale=x.flow.locale)
            cat.register_entity_ref(flow)
    else:
        # no ref, so nothing to anchor the flow to- we use it just for the lookup
        ref_q = _get_canonical(x.origin, x.flow.quantity_ref)
        flow = LcFlow.new(x.flow.flowable, ref_q,
                          context=tuple(x.flow.context), locale=x.flow.locale)
    if x.type == 'context':
        term = tuple(x.context)
    else:
        term = x.termination
    return ExchangeRef(p, flow, x.direction, value=x.value, termination=term)


@qdb_router.post('/{quantity_id}/do_lcia', response_model=List[DetailedLciaResult])
def post_lcia_exchanges(quantity_id: str, exchanges: List[UnallocatedExchange], locale: str=None):
    """

    no param origin: for now, let's say you can only post lcia to canonical quantities (i.e. /load first)
    :param quantity_id:
    :param exchanges: NOTE: the UnallocatedExchange model is identical to the ExchangeRef
    :param locale: used by implementation
    :return:
    """
    q = _get_canonical(None, quantity_id)
    p = LcProcess.new('LCIA POST')
    inv = [_lcia_exch_ref(p, x) for x in exchanges]
    ress = do_lcia(lcia, q, inv, locale=locale)
    return [DetailedLciaResult.from_lcia_result(p, res) for res in ress]

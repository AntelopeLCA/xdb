from api.models.response import QdbMeta
from .runtime import cat, search_entities
from fastapi import APIRouter, HTTPException
from typing import List, Optional

import re

from antelope import EntityNotFound, UnknownOrigin
from antelope_core.models import Entity, Context, Characterization
from antelope_core.entities import MetaQuantityUnit

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
            q = cat.query(origin).get_canonical(quantity)
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




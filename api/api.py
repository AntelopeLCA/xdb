from .models.response import *

from etl import run_static_catalog, CONFIG_ORIGINS, CAT_ROOT

from antelope import EntityNotFound, MultipleReferences, NoReference

from pydantic import ValidationError


from fastapi import FastAPI, HTTPException
from typing import List
import logging
import os

import sys

sys.setrecursionlimit(100)

cat = run_static_catalog(CAT_ROOT)

_ETYPES = ('processes', 'flows', 'quantities', 'lcia_methods', 'contexts')

LOGLEVEL = os.environ.get('LOGLEVEL', default='WARNING').upper()
logging.basicConfig(level=LOGLEVEL)

app = FastAPI(
    title="XDB API",
    version="0.0.1",
    description="API for the exchange database"
)

@app.get("/", response_model=ServerMeta)
def get_server_meta():
    sm = ServerMeta.from_app(app)
    for org in cat.origins:
        if org in CONFIG_ORIGINS:
            sm.origins.append(org)
    return sm


@app.get("/origins", response_model=List[str])
def get_origins():
    return [org for org in cat.origins if org in CONFIG_ORIGINS]


@app.get("/{origin}/", response_model=OriginMeta)
def get_origin(origin: str):
    return {
        "origin": origin,
        "interfaces": list(set([k.split(':')[1] for k in cat.interfaces if k.startswith(origin)]))
    }


@app.get("/{origin}/count")
def get_count(origin: str):
    q = cat.query(origin)
    return {
        'processes': q.count('process'),
        'flows': q.count('flow'),
        'quantities': q.count('quantity'),
        'flowables': len(list(q.flowables())),
        'contexts': len(list(q.contexts()))
    }


def _search_entities(query, etype, count=50, **kwargs):
    sargs = {k:v for k, v in filter(lambda x: x[1] is not None, kwargs.items())}
    if etype not in _ETYPES:
        raise HTTPException(404, "Invalid entity type %s" % etype)
    try:
        it = getattr(query, etype)(**sargs)
    except AttributeError:
        raise HTTPException(404, "Unknown entity type %s" % etype)
    for e in it:
        if e.origin != query.origin:
            continue
        yield Entity.from_entity(e, **sargs)
        count -= 1
        if count <= 0:
            break


@app.get("/{origin}/processes") # , response_model=List[Entity])
async def search_processes(origin:str,
                           name: Optional[str]=None,
                           classifications: Optional[str]=None,
                           spatialscope: Optional[str]=None,
                           comment: Optional[str]=None):
    query = cat.query(origin)
    kwargs = {'name': name,
              'classifications': classifications,
              'spatialscope': spatialscope,
              'comment': comment}
    return list(_search_entities(query, 'processes', **kwargs))

@app.get("/{origin}/flows", response_model=List[Entity])
def search_flows(origin:str,
                 name: Optional[str]=None,
                 casnumber: Optional[str]=None):
    kwargs = {'name': name,
              'casnumber': casnumber}
    query = cat.query(origin)
    return list(_search_entities(query, 'flows', **kwargs))

@app.get("/{origin}/quantities", response_model=List[Entity])
def search_quantities(origin:str,
                      name: Optional[str]=None,
                      referenceunit: Optional[str]=None):
    kwargs = {'name': name,
              'referenceunit': referenceunit}
    query = cat.query(origin)
    return list(_search_entities(query, 'quantities', **kwargs))

@app.get("/{origin}/lcia_methods", response_model=List[Entity])
def search_lcia_methods(origin:str,
                        name: Optional[str]=None,
                        referenceunit: Optional[str]=None,
                        method: Optional[str]=None,
                        category: Optional[str]=None,
                        indicator: Optional[str]=None):
    kwargs = {'name': name,
              'referenceunit': referenceunit,
              'method': method,
              'category': category,
              'indicator': indicator}
    query = cat.query(origin)
    return list(_search_entities(query, 'lcia_methods', **kwargs))


@app.get("/{origin}/contexts", response_model=List[Context])
def get_contexts(origin: str, elementary: bool=None, sense=None, parent=None):
    q = cat.query(origin)
    if parent is not None:
        parent = q.get_context(parent)
    cxs = [Context.from_context(cx) for cx in q.contexts()]
    if elementary is not None:
        cxs = filter(lambda x: x.elementary == elementary, cxs)
    if sense is not None:
        cxs = filter(lambda x: x.sense == sense, cxs)
    if parent is not None:
        cxs = filter(lambda x: x.parent == parent, cxs)
    return list(cxs)


@app.get("/{origin}/contexts/{context}", response_model=Context)
def get_contexts(origin: str, context: str):
    q = cat.query(origin)
    return Context.from_context(q.get_context(context))


@app.get("/{origin}/{entity}", response_model=Entity)
def get_entity(origin: str, entity: str):
    try:
        e = cat.query(origin).get(entity)
    except EntityNotFound:
        raise HTTPException(404, "Entity %s not found" % entity)
    if e is None:
        raise HTTPException(404, "Entity %s is None" % entity)
    ent = Entity.from_entity(e)
    if e.entity_type == 'process':
        ent.properties[e.reference_field] = [ReferenceExchange.from_exchange(x) for x in e.reference_entity]
    elif e.entity_type == 'flow':
        ent.properties[e.reference_field] = e.reference_entity.name
    else:
        ent.properties[e.reference_field] = str(e.reference_entity)
    for p in e.properties():
        ent.properties[p] = e[p]
    return ent

def _get_typed_entity(origin, entity, etype):
    e = get_entity(origin, entity)
    if e.entity_type == etype:
        return e
    raise HTTPException(400, detail="entity %s is not a %s" % (entity, etype))


@app.get("/{origin}/processes/{entity}/", response_model=Entity)
def get_named_process(origin: str, entity: str):
    return _get_typed_entity(origin, entity, 'process')

@app.get("/{origin}/flows/{entity}/", response_model=Entity)
def get_named_flow(origin: str, entity: str):
    return _get_typed_entity(origin, entity, 'flow')

@app.get("/{origin}/quantities/{entity}/", response_model=Entity)
@app.get("/{origin}/flowproperties/{entity}/", response_model=Entity)
@app.get("/{origin}/flow_properties/{entity}/", response_model=Entity)
@app.get("/{origin}/lciamethods/{entity}/", response_model=Entity)
@app.get("/{origin}/lcia_methods/{entity}/", response_model=Entity)
def get_named_quantity(origin: str, entity: str):
    return _get_typed_entity(origin, entity, 'quantity')


@app.get("/{origin}/{entity}/reference")
def get_unitary_reference(origin, entity):
    """
    Response model varies with entity type (!)
    Quantity: reference is unit
    Flow: reference is quantity (unit)
    Process: reference is ReferenceExchange or an exception
    :param origin:
    :param entity:
    :return:
    """
    ent = cat.query(origin).get(entity)
    if ent.entity_type == 'quantity':
        return ent.unit
    elif ent.entity_type == 'process':
        try:
            rx = ReferenceExchange.from_exchange(ent.reference())
        except MultipleReferences:
            raise HTTPException(404, f"Process {entity} has multiple references")
        except NoReference:
            raise HTTPException(404, f"Process {entity} has no references")
        return rx

    else:  # if ent.entity_type == 'flow':
        return Entity.from_entity(ent.reference_entity)


"""TO WRITE:
/{origin}/{entity}/properties
/{origin}/{entity}/references

/{origin}/{flow}/unit
/{origin}/{flow}/context
/{origin}/{flow}/location ???
/{origin}/{flow}/targets

/{origin}/{process}/exchanges
/{origin}/{process}/exchange_values
/{origin}/{process}/inventory


"""
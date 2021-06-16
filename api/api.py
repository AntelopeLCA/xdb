from .models.response import *

from etl import run_static_catalog, CONFIG_ORIGINS, CAT_ROOT

from antelope import EntityNotFound, MultipleReferences, NoReference, check_direction, EXCHANGE_TYPES



from fastapi import FastAPI, HTTPException
from typing import List
import logging
import os

import sys

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
        if not e.origin.startswith(query.origin):  # return more-specific
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


@app.get("/{origin}/{entity}/references")
def get_references(origin, entity):
    ent = cat.query(origin).get(entity)
    if ent.entity_type == 'process':
        return list(ReferenceValue.from_rx(rx) for rx in ent.references())
    else:
        return [get_unitary_reference(origin, entity)]


@app.get("/{origin}/{entity}/unit")
def get_unit(origin, entity):
    return getattr(cat.query(origin).get(entity), 'unit')

@app.get("/{origin}/{flow}/context", response_model=Context)
def get_targets(origin, flow):
    q = cat.query(origin)
    f = q.get(flow)
    cx = q.get_context(f.context)  # can't remember if flow is already context-equipped
    return Context.from_context(cx)


"""TO WRITE:
/{origin}/{entity}/properties

/{origin}/{flow}/location ???

/{origin}/{flow}/emitters

"""
'''
Routes that return exchanges
'''

@app.get("/{origin}/{flow}/targets", response_model=List[ReferenceExchange])
def get_targets(origin, flow, direction: str=None):
    if direction is not None:
        direction = check_direction(direction)
    return list(ReferenceExchange.from_exchange(x) for x in cat.query(origin).targets(flow, direction=direction))


@app.get("/{origin}/{process}/exchanges", response_model=List[Exchange])
def get_exchanges(origin, process, type: str=None, flow: str=None):
    if type and (type not in EXCHANGE_TYPES):
        raise HTTPException(400, detail=f"Cannot understand type {type}")
    p = cat.query(origin).get(process)
    exch = p.exchanges(flow=flow)
    return list(generate_pydantic_exchanges(exch, type=type))


@app.get("/{origin}/{process}/exchanges/{flow}", response_model=List[ExchangeValue])
def get_exchange_values(origin, process, flow: str):
    p = cat.query(origin).get(process)
    exch = p.exchange_values(flow=flow)
    return list(ExchangeValue.from_ev(x) for x in exch)


@app.get("/{origin}/{process}/inventory")
def get_inventory(origin, process, ref_flow: str=None):
    p = cat.query(origin).get(process)
    try:
        rx = p.reference(ref_flow)
    except MultipleReferences:
        raise HTTPException(404, f"Process {process} has multiple references")
    except NoReference:
        raise HTTPException(404, f"Process {process} has no references")

    inv = p.inventory(rx)
    return list(AllocatedExchange.from_inv(x, rx.flow.external_ref) for x in inv)


'''
Routes that depend on topological ordering

/{origin}/foreground  [ReferenceExchange]
/{origin}/background  [ReferenceExchange]
/{origin}/interior    [ReferenceExchange]
/{origin}/exterior    [ExteriorFlow]

/{origin}/{process}/{ref_flow}/dependencies  [AllocatedExchange]; term is node
/{origin}/{process}/{ref_flow}/emissions     [AllocatedExchange]; term is context
## fair question whether cutoffs should include non-elementary contexts-
## related: are cutoffs a subset of emissions, disjoint, or intersect?
Standard usage: "emissions" are elementary, "cutoffs" are dangling. Problem is,
that predicates the response on having an LciaEngine to resolve the contexts, and 
present Background impl does not: it asks its local _index. now we could just give
every term manager the set of default contexts... what other differences exist? 
/{origin}/{process}/{ref_flow}/cutoffs       [AllocatedExchange]; term is None 

/{origin}/{process}/{ref_flow}/consumers    [ReferenceExchange]
/{origin}/{process}/{ref_flow}/foreground   [one ReferenceExchange followed by AllocatedExchanges]

/{origin}/{process}/{ref_flow}/ad           [AllocatedExchange]
/{origin}/{process}/{ref_flow}/bf           [AllocatedExchange]
/{origin}/{process}/{ref_flow}/lci            [AllocatedExchange]
/{origin}/{process}/{ref_flow}/lci/{ext_flow} [AllocatedExchange]

/{origin}/{process}/{ref_flow}/syslci [POST]  [AllocatedExchange]

'''

@app.get('/{origin}/{process}/{ref_flow}/ad', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/ad', response_model=List[AllocatedExchange])
def get_ad(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.ad(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/bf', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/bf', response_model=List[AllocatedExchange])
def get_bf(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.bf(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/dependencies', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/dependencies', response_model=List[AllocatedExchange])
def get_dependencies(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.dependencies(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/emissions', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/emissions', response_model=List[AllocatedExchange])
def get_emissions(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.emissions(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/cutoffs', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/cutoffs', response_model=List[AllocatedExchange])
def get_cutoffs(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.cutoffs(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/lci', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/lci', response_model=List[AllocatedExchange])
def get_lci(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.lci(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/consumers', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/consumers', response_model=List[AllocatedExchange])
def get_consumers(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    return list(ReferenceExchange.from_exchange(x) for x in p.consumers(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/foreground', response_model=List[ExchangeValue])
@app.get('/{origin}/{process}/foreground', response_model=List[ExchangeValue])
def get_foreground(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = p.reference(ref_flow)
    fg = p.foreground(ref_flow=rf)
    rtn = [ReferenceValue.from_rx(next(fg))]
    for dx in fg:
        rtn.append(ExchangeValue.from_ev(dx))
    return rtn

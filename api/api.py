from antelope_core.models import *
from antelope_core.entities import MetaQuantityUnit

from api.models.response import ServerMeta

from .runtime import CONFIG_ORIGINS, cat, search_entities
from .qdb import qdb_router

from antelope import EntityNotFound, MultipleReferences, NoReference, check_direction, EXCHANGE_TYPES, IndexRequired

from fastapi import FastAPI, HTTPException
from typing import List
import logging
import os



LOGLEVEL = os.environ.get('LOGLEVEL', default='WARNING').upper()
logging.basicConfig(level=LOGLEVEL)

app = FastAPI(
    title="XDB API",
    version="0.0.1",
    description="API for the exchange database"
)

app.include_router(qdb_router)


@app.get("/", response_model=ServerMeta)
def get_server_meta():
    sm = ServerMeta.from_app(app)
    for org in cat.origins:
        sm.origins.append(org)
        if org in CONFIG_ORIGINS:
            sm.config_origins.append(org)
    return sm


def _get_authorized_query(origin):
    """
    The main point of this is to ask the auth server / oauth grant / etc what the supplied credentials authorize
    with respect to the stated origin.

    The way I had imagined this was:
    the service we offer is trusted [in two senses] computation in a private setting. The user has paid to activate
    the container (like a holosuite / DS9) and they have access to: free stuff, ecoinvent, other subscriptions,
    their private data, private data that's been shared with them. all that is specified by semantic origin, which
    has the format:

    [origin]/query
    [origin]/[dataset]/query

    and origin specifies the provider, resource, and scope (e.g. version) of the query.

    so, e.g. ecoinvent.3.4.cutoff/uuid0123-4567-.../exchanges/flow9876-5432-*

    Auth grants look like:

    AuthGrant(ResponseModel):
        auth: apiToken
        origin: str
        interface: [one of READONLY_INTERFACE_TYPES]
        read: True  # existence of the grant implies read access ??
        values: bool  # access to numerical data [exchange values; characterization results]
        write: bool  # permission to update data [within the specified interface]

    under consideration:
        masq: bool  # whether to conceal sub-origins

    Somehow we need / want to implement a sort of mapping where detailed origins are presented as higher-level
    origins for external query. For instance, an XDB may have the following origins on hand:
      - lcacommons.uslci.fy2020.q3
      - lcacommons.uslci.fy2020.q4
      - lcacommons.uslci.fy2021.q1
    but we would like to configure only one of them to be the origin of record in response to 'lcacommons.uslci'
    queries.  Ultimately this may depend on the user's authorization-- certain users may have access to all the
    different version, but others will only get 'lcacommons.uslci'

    We also need to decide whether to "masquerade" the true origin or not, i.e. if a user is authorized for
    'lcacommons.uslci' and the origin of record is 'lcacommons.uslci.fy2021.q1', do the queries include the true
    origin or the authorized one? I would tend toward the true origin. this is the masq[uerade] question.

    :param origin:
    :return:
    """
    pass



@app.get("/origins", response_model=List[str])
def get_origins():
    return [org for org in cat.origins if org in CONFIG_ORIGINS]


def _origin_meta(origin):
    """
    It may well be that OriginMeta needs to include config information (at minimum, context hints)- in which
    case the meta object should be constructed from resources, not from blackbox queries. we shall see
    :param origin:
    :return:
    """
    is_lcia = cat.query(origin).is_lcia_engine()
    return {
        "origin": origin,
        "is_lcia_engine": is_lcia,
        "interfaces": list(set([k.split(':')[1] for k in cat.interfaces if k.startswith(origin)]))
    }


@app.get("/{origin}/", response_model=List[OriginMeta])
def get_origin(origin: str):
    """
    TODO: reconcile the AVAILABLE origins with the CONFIGURED origins and the AUTHORIZED origins
    :param origin:
    :return:
    """
    return [_origin_meta(org) for org in cat.origins if org.startswith(origin)]


@app.get("/{origin}/synonyms", response_model=List[str])
def get_synonyms(origin:str, term: str):
    return cat.query(origin).synonyms(term)



@app.get("/{origin}/count", response_model=List[OriginCount])
def get_origin(origin:str):
    return list(_get_origin_counts(origin))



def _get_origin_counts(origin: str):
    for org in cat.origins:
        if not org.startswith(origin):
            continue
        try:
            q = cat.query(org)
            yield {
                'origin': org,
                'count': {
                    'processes': q.count('process'),
                    'flows': q.count('flow'),
                    'quantities': q.count('quantity'),
                    'flowables': len(list(q.flowables())),
                    'contexts': len(list(q.contexts()))
                }
            }
        except IndexRequired:
            pass

'''
Index Interface
'''
@app.get("/{origin}/processes") # , response_model=List[Entity])
def search_processes(origin:str,
                     name: Optional[str]=None,
                     classifications: Optional[str]=None,
                     spatialscope: Optional[str]=None,
                     comment: Optional[str]=None):
    query = cat.query(origin)
    kwargs = {'name': name,
              'classifications': classifications,
              'spatialscope': spatialscope,
              'comment': comment}
    return list(search_entities(query, 'processes', **kwargs))

@app.get("/{origin}/flows", response_model=List[FlowEntity])
def search_flows(origin:str,
                 name: Optional[str]=None,
                 casnumber: Optional[str]=None):
    kwargs = {'name': name,
              'casnumber': casnumber}
    query = cat.query(origin)
    return list(search_entities(query, 'flows', **kwargs))

@app.get("/{origin}/quantities", response_model=List[Entity])
def search_quantities(origin:str,
                      name: Optional[str]=None,
                      referenceunit: Optional[str]=None):
    kwargs = {'name': name,
              'referenceunit': referenceunit}
    query = cat.query(origin)
    return list(search_entities(query, 'quantities', **kwargs))

@app.get("/{origin}/lcia_methods", response_model=List[Entity])
@app.get("/{origin}/lciamethods", response_model=List[Entity])
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
    return list(search_entities(query, 'lcia_methods', **kwargs))


@app.get("/{origin}/lcia", response_model=List[Entity])
def get_meta_quantities(origin,
                        name: Optional[str] = None,
                        method: Optional[str] = None):
    kwargs = {'name': name,
              'method': method}
    query = cat.query(origin)
    return list(search_entities(query, 'quantities', unit=MetaQuantityUnit.unitstring, **kwargs))


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


@app.get("/{origin}/{flow}/targets", response_model=List[ReferenceExchange])
def get_targets(origin, flow, direction: str=None):
    if direction is not None:
        direction = check_direction(direction)
    return list(ReferenceExchange.from_exchange(x) for x in cat.query(origin).targets(flow, direction=direction))


'''
Basic interface
(Listed after index interface b/c route resolution precedence
'''

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
def get_flow_context(origin, flow):
    q = cat.query(origin)
    f = q.get(flow)
    cx = q.get_context(f.context)  # can't remember if flow is already context-equipped
    return Context.from_context(cx)


def _get_rx_by_ref_flow(p, ref_flow):
    """
    This is really a bad request because either a path param or a query param was missing
    :param p:
    :param ref_flow: could be None if p has a unitary reference
    :return:
    """
    try:
        return p.reference(ref_flow)
    except MultipleReferences:
        raise HTTPException(400, f"Process {p} has multiple references")
    except NoReference:
        raise HTTPException(400, f"Process {p} has no references")


@app.get("/{origin}/{process}/lcia/{quantity}", response_model=DetailedLciaResult)
@app.get("/{origin}/{process}/lcia/{qty_org}/{quantity}", response_model=DetailedLciaResult)
@app.get("/{origin}/{process}/{ref_flow}/lcia/{quantity}", response_model=DetailedLciaResult)
@app.get("/{origin}/{process}/{ref_flow}/lcia/{qty_org}/{quantity}", response_model=DetailedLciaResult)
def get_remote_lcia(origin: str, process: str, quantity: str, ref_flow: str=None, qty_org: str=None):
    pq = cat.query(origin)
    p = pq.get(process)
    rx = _get_rx_by_ref_flow(p, ref_flow)
    if qty_org is None:
        q = cat.lcia_engine.get_canonical(quantity)
    else:
        q = cat.query(qty_org).get_canonical(quantity)
    # check authorization for detailed Lcia
    res = q.do_lcia(p.lci(rx))
    if True:
        return DetailedLciaResult.from_lcia_result(p, res)
    else:
        return SummaryLciaResult.from_lcia_result(p, res)


"""TO WRITE:
/{origin}/{entity}/properties

/{origin}/{flow}/locale ???

/{origin}/{flow}/emitters

"""
'''
exchange interface
'''
@app.get("/{origin}/{process}/exchanges", response_model=List[Exchange])
def get_exchanges(origin, process, type: str=None, flow: str=None):
    if type and (type not in EXCHANGE_TYPES):
        raise HTTPException(400, detail=f"Cannot understand type {type}")
    p = cat.query(origin).get(process)
    exch = p.exchanges(flow=flow)
    return list(generate_pydantic_exchanges(exch, type=type))


@app.get("/{origin}/{process}/exchanges/{flow}", response_model=List[ExchangeValues])
def get_exchange_values(origin, process, flow: str):
    p = cat.query(origin).get(process)
    exch = p.exchange_values(flow=flow)
    return list(ExchangeValues.from_ev(x) for x in exch)


@app.get("/{origin}/{process}/inventory", response_model=List[AllocatedExchange])
@app.get("/{origin}/{process}/{ref_flow}/inventory", response_model=List[AllocatedExchange])
def get_inventory(origin, process, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rx = _get_rx_by_ref_flow(process, ref_flow)

    inv = p.inventory(rx)
    return list(AllocatedExchange.from_inv(x, rx.flow.external_ref) for x in inv)


'''
background interface

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
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.ad(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/bf', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/bf', response_model=List[AllocatedExchange])
def get_bf(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.bf(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/dependencies', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/dependencies', response_model=List[AllocatedExchange])
def get_dependencies(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.dependencies(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/emissions', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/emissions', response_model=List[AllocatedExchange])
def get_emissions(origin: str, process: str, ref_flow: str=None):
    """
    This returns a list of elementary exchanges from the process+reference flow pair.
    :param origin:
    :param process:
    :param ref_flow:
    :return:
    """

    p = cat.query(origin).get(process)
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.emissions(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/cutoffs', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/cutoffs', response_model=List[AllocatedExchange])
def get_cutoffs(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.cutoffs(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/lci', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/lci', response_model=List[AllocatedExchange])
def get_lci(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.lci(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/consumers', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/consumers', response_model=List[AllocatedExchange])
def get_consumers(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(ReferenceExchange.from_exchange(x) for x in p.consumers(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/foreground', response_model=List[ExchangeValues])
@app.get('/{origin}/{process}/foreground', response_model=List[ExchangeValues])
def get_foreground(origin: str, process: str, ref_flow: str=None):
    p = cat.query(origin).get(process)
    rf = _get_rx_by_ref_flow(p, ref_flow)
    fg = p.foreground(ref_flow=rf)
    rtn = [ReferenceValue.from_rx(next(fg))]
    for dx in fg:
        rtn.append(ExchangeValues.from_ev(dx))
    return rtn


'''
quantity interface
key question: is_lcia_engine() bool returns whether the source performs input harmonization, e.g. whether it supports
the POST routes:
    APIv2ROOT/[origin]/[quantity id]/factors POST flow specs (or exterior flows?)- map flow spec to factors
    APIv2ROOT/[origin]/[quantity]/lcia POST exchanges- returns an LciaResult

Now, a source-specific quantity interface, which is necessary to expose non-harmonized quantity data from 
xdb data sources.

The main characteristic of these routes is that they use each archive's term manager instead of the catalog's quantity
manager. 

Applicable routes:

    Origin-specific (implemented above)
    APIv2_ROOT/[origin]/synonyms?term=term      - list synonyms for the specified term
    APIv2_ROOT/[origin]/contexts/[term]         - return canonical full context for term

    Entity-specific
    APIv2_ROOT/[origin]/[flow id]/profile       - list characterizations for the flow
    APIv2_ROOT/[origin]/[flow id]/cf/[quantity id] - return the characterization value as a float (or 0.0)

    APIv2_ROOT/[origin]/[quantity id]/norm      - return a normalization dict
    APIv2_ROOT/[origin]/[quantity id]/factors   - list characterizations for the quantity
    APIv2_ROOT/[origin]/[quantity id]/convert/[flow id] - return a QuantityConversion
    APIv2_ROOT/[origin]/[quantity id]/convert/[flowable]/[ref quantity] - return a QuantityConversion
    
    APIv2_ROOT/[origin]/[quantity id]/lcia {POST} - perform LCIA on POSTDATA = list of exchange refs

'''

@app.get('/{origin}/{flow_id}/profile', response_model=List[Characterization])
def get_flow_profile(origin: str, flow_id: str, quantity: str=None, context: str=None):
    f = cat.query(origin).get(flow_id)
    if quantity is not None:
        quantity = cat.query(origin).get(quantity)
    if context is not None:
        context = cat.query(origin).get_context(context)
    return [Characterization.from_cf(cf) for cf in f.profile(quantity=quantity, context=context)]


@app.get('/{origin}/{quantity_id}/norm', response_model=Normalizations)
def get_quantity_norms(origin:str, quantity_id: str):
    q = cat.query(origin).get(quantity_id)
    return Normalizations.from_q(q)


@app.get('/{origin}/{quantity_id}/factors', response_model=List[Characterization])
@app.get('/{origin}/{quantity_id}/factors/{flowable}', response_model=List[Characterization])
def get_quantity_norms(origin:str, quantity_id: str, flowable: str=None):
    q = cat.query(origin).get(quantity_id)
    enum = q.factors(flowable=flowable)

    return list(Characterization.from_cf(cf) for cf in enum)


@app.post('/{origin}/{quantity_id}/lcia', response_model=DetailedLciaResult)
def do_lcia_by_post(origin: str, quantity_id: str, exchanges: List[UnallocatedExchange]):
    """

    :param origin:
    :param quantity_id:
    :param exchanges: NOTE: the UnallocatedExchange model is identical to the ExchangeRef
    :return:
    """
    q = cat.query(origin)
    pass




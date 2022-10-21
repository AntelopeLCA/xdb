from antelope_core.models import (OriginMeta, OriginCount, Entity, FlowEntity, Context, Exchange, ReferenceExchange,
                                  ExchangeValues, ReferenceValue, DetailedLciaResult, SummaryLciaResult,
                                  AllocatedExchange, Characterization, Normalizations,
                                  generate_pydantic_exchanges)

from antelope_core.entities import MetaQuantityUnit
from antelope_core.auth import AuthorizationGrant, JwtGrant

from .models.response import ServerMeta, PostTerm

from .runtime import PUBLIC_ORIGINS, UNRESTRICTED_GRANTS, cat, search_entities, do_lcia, PUBKEYS
from .qdb import qdb_router

from antelope import EntityNotFound, MultipleReferences, NoReference, check_direction, EXCHANGE_TYPES, IndexRequired

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from typing import List, Optional
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


oauth2_scheme = OAuth2PasswordBearer(auto_error=False, tokenUrl="token")  # the tokenUrl argument appears to do nothing

"""
Our implied auth database requires the following tables (basically all the stuff in runtime.py):

PUBKEYS of public keys associated with valid token issuers (revocable / managed)
ORIGINS and their maintainers 
ISSUES which pair an origin, issuer, and interface (enum), possibly with other auth metadata

Issues with the master issuer can be considered "public" interfaces, because of a policy that the auth server will 
issue a token for a public interface to any user (subject to usage constraints) 

[or: issues with None issuer do not require tokens]

The db content is presently provided in digested form as PUBKEYS (containing 1 entry), PUBLIC_ORIGINS and 
UNRESTRICTED_GRANTS, with all other grants being assumed to be delivered by JWT (nonstatically)

qdb is mainly where usage is metered for public data

but also, the issuing of tokens is metered- a free user will get say 15 or 25 sessions/month




"""


def get_token_grants(token: Optional[str]):
    if token is None:
        return []
    payload = jwt.decode(token, 'a fish', options={'verify_signature': False})
    try:
        pub = PUBKEYS[payload['iss']]  # this tells us the issuer signed this token
    except KeyError:
        raise HTTPException(401, detail='Issuer %s unknown' % payload['iss'])
    try:
        valid_payload = jwt.decode(token, pub, algorithms=['RS256'])
    except JWTError:
        raise HTTPException(401, detail='Token failed verification')
    # however, we also need to test whether the issuer is trusted with the requested origin(s). otherwise one
    # compromised key would allow a user to issue a token for any origin
    return AuthorizationGrant.from_jwt(JwtGrant(**valid_payload))


@app.get("/", response_model=ServerMeta)
def get_server_meta(token: Optional[str] = Depends(oauth2_scheme)):
    grants = get_token_grants(token)
    sm = ServerMeta.from_app(app)
    for org in PUBLIC_ORIGINS:
        sm.origins.append(org)
    for org in sorted(set(k.origin for k in grants)):
        sm.authorized_origins.append(org)
    return sm


def _get_authorized_query(origin, token):
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

    Auth grants look like (see antelope_core.auth):

    AuthorizationGrant(ResponseModel):
        auth: apiToken
        origin: str
        access: [one of READONLY_INTERFACE_TYPES]
        # read: True  # existence of the grant implies read access
        values: bool  # access to numerical data [exchange values; characterization results]
        update: bool  # permission to update data [within the specified interface]

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
    :return: a catalog query, with an authorized_interfaces attribute that returns: a set of authorizations. spec tbd.
    """
    auth_grants = get_token_grants(token)
    grants = UNRESTRICTED_GRANTS + auth_grants
    q = cat.query(origin, grants=grants)  # XdbCatalog will return an XdbQuery which auto-enforces grants !!
    # q.authorized_interfaces = set([k.split(':')[1] for k in cat.interfaces if k.startswith(origin)])
    return q


@app.get("/origins", response_model=List[str])
def get_origins(token: Optional[str] = Depends(oauth2_scheme)):
    auth_grants = get_token_grants(token)
    all_origins = PUBLIC_ORIGINS + list(set(k.origin for k in auth_grants))
    return [org for org in all_origins if cat.known_origin(org)]


def _origin_meta(origin, token):
    """
    It may well be that OriginMeta needs to include config information (at minimum, context hints)- in which
    case the meta object should be constructed from resources, not from blackbox queries. we shall see
    :param origin:
    :return:
    """
    is_lcia = _get_authorized_query(origin, token).is_lcia_engine()
    return {
        "origin": origin,
        "is_lcia_engine": is_lcia,
        "interfaces": list(set([k.split(':')[1] for k in cat.interfaces if k.startswith(origin)]))
    }


@app.get("/{origin}/", response_model=List[OriginMeta])
def get_origin(origin: str, token: Optional[str] = Depends(oauth2_scheme)):
    """
    TODO: reconcile the AVAILABLE origins with the CONFIGURED origins and the AUTHORIZED origins
    :param origin:
    :param token:
    :return:
    """
    return [_origin_meta(org, token) for org in cat.origins if org.startswith(origin)]


@app.get("/{origin}/synonyms", response_model=List[str])
@app.get("/{origin}/synonyms/{term}", response_model=List[str])
def get_synonyms(origin: str, term: str, token: Optional[str] = Depends(oauth2_scheme)):
    return _get_authorized_query(origin, token).synonyms(term)


@app.post("/{origin}/synonyms", response_model=List[str])
def post_synonyms(origin: str, post_term: PostTerm, token: Optional[str] = Depends(oauth2_scheme)):
    return _get_authorized_query(origin, token).synonyms(post_term.term)


@app.get("/{origin}/count", response_model=List[OriginCount])
def get_origin(origin: str, token: Optional[str] = Depends(oauth2_scheme)):
    return list(_get_origin_counts(origin, token))


def _get_origin_counts(origin: str, token: Optional[str]):
    for org in cat.origins:
        if not org.startswith(origin):
            continue
        try:
            q = _get_authorized_query(org, token)
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


@app.get("/{origin}/processes")  # , response_model=List[Entity])
def search_processes(origin: str,
                     name: Optional[str] = None,
                     classifications: Optional[str] = None,
                     spatialscope: Optional[str] = None,
                     comment: Optional[str] = None,
                     token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    kwargs = {'name': name,
              'classifications': classifications,
              'spatialscope': spatialscope,
              'comment': comment}
    return list(search_entities(query, 'processes', **kwargs))


@app.get("/{origin}/flows", response_model=List[FlowEntity])
def search_flows(origin: str,
                 name: Optional[str] = None,
                 casnumber: Optional[str] = None,
                 token: Optional[str] = Depends(oauth2_scheme)):
    kwargs = {'name': name,
              'casnumber': casnumber}
    query = _get_authorized_query(origin, token)
    return list(search_entities(query, 'flows', **kwargs))


@app.get("/{origin}/quantities", response_model=List[Entity])
def search_quantities(origin: str,
                      name: Optional[str] = None,
                      referenceunit: Optional[str] = None,
                      token: Optional[str] = Depends(oauth2_scheme)):
    kwargs = {'name': name,
              'referenceunit': referenceunit}
    query = _get_authorized_query(origin, token)
    return list(search_entities(query, 'quantities', **kwargs))


@app.get("/{origin}/lcia_methods", response_model=List[Entity])
@app.get("/{origin}/lciamethods", response_model=List[Entity])
def search_lcia_methods(origin: str,
                        name: Optional[str] = None,
                        referenceunit: Optional[str] = None,
                        method: Optional[str] = None,
                        category: Optional[str] = None,
                        indicator: Optional[str] = None,
                        token: Optional[str] = Depends(oauth2_scheme)):
    kwargs = {'name': name,
              'referenceunit': referenceunit,
              'method': method,
              'category': category,
              'indicator': indicator}
    query = _get_authorized_query(origin, token)
    return list(search_entities(query, 'lcia_methods', **kwargs))


@app.get("/{origin}/lcia", response_model=List[Entity])
def get_meta_quantities(origin,
                        name: Optional[str] = None,
                        method: Optional[str] = None,
                        token: Optional[str] = Depends(oauth2_scheme)):
    kwargs = {'name': name,
              'method': method}
    query = _get_authorized_query(origin, token)
    return list(search_entities(query, 'quantities', unit=MetaQuantityUnit.unitstring, **kwargs))


@app.get("/{origin}/contexts", response_model=List[Context])
def get_contexts(origin: str, elementary: bool = None, sense=None, parent=None,
                 token: Optional[str] = Depends(oauth2_scheme)):
    q = _get_authorized_query(origin, token)
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
def get_context(origin: str, context: str,
                token: Optional[str] = Depends(oauth2_scheme)):
    q = _get_authorized_query(origin, token)
    return Context.from_context(q.get_context(context))


@app.get("/{origin}/{flow}/targets", response_model=List[ReferenceExchange])
def get_targets(origin, flow, direction: str = None,
                token: Optional[str] = Depends(oauth2_scheme)):
    if direction is not None:
        direction = check_direction(direction)
    return list(ReferenceExchange.from_exchange(x) for x in
                _get_authorized_query(origin, token).targets(flow, direction=direction))


'''
Basic interface
(Listed after index interface b/c route resolution precedence
'''


def _get_typed_entity(q, entity, etype=None):
    try:
        e = q.get(entity)
    except EntityNotFound:
        raise HTTPException(404, "Entity %s not found" % entity)
    if e is None:
        raise HTTPException(404, "Entity %s is None" % entity)
    if etype is None or e.entity_type == etype:
        return e
    raise HTTPException(400, detail="entity %s is not a %s" % (entity, etype))


@app.get("/{origin}/{entity}", response_model=Entity)
def get_entity(origin: str, entity: str,
               token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    e = _get_typed_entity(query, entity)
    if e.entity_type == 'process':
        ent = Entity.from_entity(e)
        ent.properties[e.reference_field] = [ReferenceExchange.from_exchange(x) for x in e.reference_entity]
    elif e.entity_type == 'flow':
        ent = FlowEntity.from_flow(e)
    else:
        ent = Entity.from_entity(e)
        ent.properties[e.reference_field] = str(e.reference_entity)
    for p in e.properties():
        try:
            ent.properties[p] = e[p]
        except KeyError as err:
            ent.properties[p] = err
    return ent


@app.get("/{origin}/processes/{entity}/", response_model=Entity)
def get_named_process(origin: str, entity: str,
                      token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    return _get_typed_entity(query, entity, 'process')


@app.get("/{origin}/flows/{entity}/", response_model=Entity)
def get_named_flow(origin: str, entity: str,
                   token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    return _get_typed_entity(query, entity, 'flow')


@app.get("/{origin}/quantities/{entity}/", response_model=Entity)
@app.get("/{origin}/flowproperties/{entity}/", response_model=Entity)
@app.get("/{origin}/flow_properties/{entity}/", response_model=Entity)
@app.get("/{origin}/lciamethods/{entity}/", response_model=Entity)
@app.get("/{origin}/lcia_methods/{entity}/", response_model=Entity)
def get_named_quantity(origin: str, entity: str,
                       token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    return _get_typed_entity(query, entity, 'quantity')


@app.get("/{origin}/{entity}/reference")  # SHOOP
def get_unitary_reference(origin, entity, token: Optional[str] = Depends(oauth2_scheme)):
    """
    Response model varies with entity type (!)
    Quantity: reference is unit
    Flow: reference is quantity (unit)
    Process: reference is ReferenceExchange or an exception
    :param origin:
    :param entity:
    :param token:
    :return:
    """
    query = _get_authorized_query(origin, token)
    ent = _get_typed_entity(query, entity)
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


@app.get("/{origin}/processes/{entity}/references")
@app.get("/{origin}/flows/{entity}/references")
@app.get("/{origin}/quantities/{entity}/references")
@app.get("/{origin}/flowproperties/{entity}/references")
@app.get("/{origin}/{entity}/references")
def get_references(origin, entity, token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    ent = _get_typed_entity(query, entity)
    if ent.entity_type == 'process':
        return list(ReferenceValue.from_rx(rx) for rx in ent.references())
    else:
        return [get_unitary_reference(origin, entity)]


@app.get("/{origin}/{entity}/uuid", response_model=str)
def get_uuid(origin, entity, token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    ent = _get_typed_entity(query, entity)
    return ent.uuid


@app.get("/{origin}/{entity}/properties", response_model=List[str])  # SHOOP
def get_properties(origin, entity, token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    ent = _get_typed_entity(query, entity)
    return list(ent.properties())


@app.get("/{origin}/{entity}/doc/{item}")  # SHOOP
def get_item(origin, entity, item, token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    ent = _get_typed_entity(query, entity)
    return ent[item]


@app.get("/{origin}/flows/{entity}/unit")  # SHOOP
@app.get("/{origin}/flowproperties/{entity}/unit")  # SHOOP
@app.get("/{origin}/quantities/{entity}/unit")  # SHOOP
@app.get("/{origin}/{entity}/unit")  # SHOOP
def get_unit(origin, entity, token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    return getattr(_get_typed_entity(query, entity), 'unit')


@app.get("/{origin}/flows/{flow}/context", response_model=Context)
@app.get("/{origin}/{flow}/context", response_model=Context)
def get_flow_context(origin, flow, token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    f = _get_typed_entity(query, flow, 'flow')
    return get_context(origin, f.context[-1])  # can't remember if flow is already context-equipped


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


@app.get("/{origin}/{process}/lcia/{quantity}", response_model=List[DetailedLciaResult])  # SHOOP
@app.get("/{origin}/{process}/lcia/{qty_org}/{quantity}", response_model=List[DetailedLciaResult])
@app.get("/{origin}/{process}/{ref_flow}/lcia/{quantity}", response_model=List[DetailedLciaResult])
@app.get("/{origin}/{process}/{ref_flow}/lcia/{qty_org}/{quantity}", response_model=List[DetailedLciaResult])
def get_remote_lcia(origin: str, process: str, quantity: str, ref_flow: str = None, qty_org: str = None,
                    token: Optional[str] = Depends(oauth2_scheme)):
    """

    :param origin:
    :param process:
    :param quantity:
    :param ref_flow: [None] if process has multiple references, one must be specified
    :param qty_org: [None] if
    :param token:
    :return:
    """
    pq = _get_authorized_query(origin, token)
    p = pq.get(process)
    rx = _get_rx_by_ref_flow(p, ref_flow)
    lci = list(p.lci(rx))

    if qty_org is None:
        try:
            qq = cat.lcia_engine.get_canonical(quantity)
        except EntityNotFound:
            raise HTTPException(404, f"Quantity {quantity} not found")
        query = _get_authorized_query(qq.origin, token)
    else:
        query = _get_authorized_query(qty_org, token)
        qq = query.get_canonical(quantity)

    ress = do_lcia(query, qq, lci)

    if 'exchange' in pq.authorized_interfaces():
        return [DetailedLciaResult.from_lcia_result(p, res) for res in ress]
    else:
        return [SummaryLciaResult.from_lcia_result(p, res) for res in ress]


"""TO WRITE:
/{origin}/{flow}/locale ???

/{origin}/{flow}/emitters

"""
'''
exchange interface
'''


@app.get("/{origin}/{process}/exchanges", response_model=List[Exchange])  # SHOOP
def get_exchanges(origin, process, type: str = None, flow: str = None,
                  token: Optional[str] = Depends(oauth2_scheme)):
    if type and (type not in EXCHANGE_TYPES):
        raise HTTPException(400, detail=f"Cannot understand type {type}")
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    exch = p.exchanges(flow=flow)
    return list(generate_pydantic_exchanges(exch, type=type))


@app.get("/{origin}/{process}/exchanges/{flow}", response_model=List[ExchangeValues])  # SHOOP
def get_exchange_values(origin, process, flow: str,
                        token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    exch = p.exchange_values(flow=flow)
    return list(ExchangeValues.from_ev(x) for x in exch)


@app.get("/{origin}/{process}/inventory", response_model=List[AllocatedExchange])
@app.get("/{origin}/{process}/{ref_flow}/inventory", response_model=List[AllocatedExchange])
def get_inventory(origin, process, ref_flow: str = None,
                  token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rx = _get_rx_by_ref_flow(p, ref_flow)

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
def get_ad(origin: str, process: str, ref_flow: str = None,
           token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.ad(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/bf', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/bf', response_model=List[AllocatedExchange])
def get_bf(origin: str, process: str, ref_flow: str = None,
           token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.bf(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/dependencies', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/dependencies', response_model=List[AllocatedExchange])
def get_dependencies(origin: str, process: str, ref_flow: str = None,
                     token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.dependencies(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/emissions', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/emissions', response_model=List[AllocatedExchange])
def get_emissions(origin: str, process: str, ref_flow: str = None,
                  token: Optional[str] = Depends(oauth2_scheme)):
    """
    This returns a list of elementary exchanges from the process+reference flow pair.
    :param origin:
    :param process:
    :param ref_flow:
    :param token:
    :return:
    """

    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.emissions(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/cutoffs', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/cutoffs', response_model=List[AllocatedExchange])
def get_cutoffs(origin: str, process: str, ref_flow: str = None,
                token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.cutoffs(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/lci', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/lci', response_model=List[AllocatedExchange])
def get_lci(origin: str, process: str, ref_flow: str = None,
            token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(AllocatedExchange.from_inv(x, ref_flow=rf.flow.external_ref) for x in p.lci(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/consumers', response_model=List[AllocatedExchange])
@app.get('/{origin}/{process}/consumers', response_model=List[AllocatedExchange])
def get_consumers(origin: str, process: str, ref_flow: str = None,
                  token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
    rf = _get_rx_by_ref_flow(p, ref_flow)
    return list(ReferenceExchange.from_exchange(x) for x in p.consumers(ref_flow=rf))


@app.get('/{origin}/{process}/{ref_flow}/foreground', response_model=List[ExchangeValues])
@app.get('/{origin}/{process}/foreground', response_model=List[ExchangeValues])
def get_foreground(origin: str, process: str, ref_flow: str = None,
                   token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    p = _get_typed_entity(query, process, 'process')
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
def get_flow_profile(origin: str, flow_id: str, quantity: str = None, context: str = None,
                     token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    f = _get_typed_entity(query, flow_id, 'flow')
    if quantity is not None:
        quantity = _get_typed_entity(query, quantity, 'quantity')
    if context is not None:
        context = query.get_context(context)
    return [Characterization.from_cf(cf) for cf in f.profile(quantity=quantity, context=context)]


@app.get('/{origin}/{quantity_id}/norm', response_model=Normalizations)
def get_quantity_norms(origin: str, quantity_id: str,
                       token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    q = _get_typed_entity(query, quantity_id, 'quantity')
    return Normalizations.from_q(q)


@app.get('/{origin}/{quantity_id}/factors', response_model=List[Characterization])
@app.get('/{origin}/{quantity_id}/factors/{flowable}', response_model=List[Characterization])
def get_quantity_norms(origin: str, quantity_id: str, flowable: str = None,
                       token: Optional[str] = Depends(oauth2_scheme)):
    query = _get_authorized_query(origin, token)
    q = _get_typed_entity(query, quantity_id, 'quantity')
    enum = q.factors(flowable=flowable)

    return list(Characterization.from_cf(cf) for cf in enum)

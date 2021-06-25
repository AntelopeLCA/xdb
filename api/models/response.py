from pydantic import BaseModel
from pydantic.typing import List, Dict, Optional


class ResponseModel(BaseModel):
    # There's good reason for having this child class later on.
    # It is to allow for global response model configuration via inheritance.
    pass


class ServerMeta(ResponseModel):
    title: str
    version: str
    description: str
    origins: List[str]

    @classmethod
    def from_app(cls, app):
        obj = cls(title=app.title,
                  version=app.version,
                  description=app.description,
                  origins=list())
        return obj


class OriginMeta(ResponseModel):
    origin: str
    interfaces: List[str]
    '''
    # report the authorization status of the query: based on auth token, what interfaces can the user access?
    read: List(str)  
    write: List(str)
    values: List(str)
    '''


class OriginCount(ResponseModel):
    origin: str
    count: dict


class Entity(ResponseModel):
    origin: str
    entity_id: str
    entity_type: str
    properties: Dict

    @classmethod
    def from_entity(cls, entity, **kwargs):
        obj = cls(origin=entity.origin,
                  entity_id=entity.external_ref,
                  entity_type=entity.entity_type,
                  properties=dict())

        obj.properties['name'] = entity.name

        for key, val in kwargs.items():
            obj.properties[key] = entity[key]
        return obj


class FlowEntity(Entity):
    """
    Open questions: should context and locale be properties? or attributes? should referenceQuantity be an attribute?
    """
    context: List[str]
    locale: str

    @classmethod
    def from_flow(cls, entity, **kwargs):
        obj = cls(origin=entity.origin,
                  entity_id=entity.external_ref,
                  entity_type=entity.entity_type,
                  context=list(entity.context),
                  locale=entity.locale,
                  properties=dict())

        obj.properties['name'] = entity.name
        obj.properties[entity.reference_field] = entity.reference_entity.external_ref

        for key, val in kwargs.items():
            obj.properties[key] = entity[key]
        return obj


class Context(ResponseModel):
    name: str
    parent: Optional[str]
    sense: Optional[str]
    elementary: bool
    subcontexts: List[str]

    @classmethod
    def from_context(cls, cx):
        if cx.parent is None:
            parent = ''
        else:
            parent = cx.parent.name
        return cls(name=cx.name, parent=parent or '', sense=cx.sense, elementary=cx.elementary,
                   subcontexts=list(k.name for k in cx.subcompartments))


class ExteriorFlow(ResponseModel):
    origin: str
    flow: str
    direction: str  # antelope_interface specifies the direction as w/r/t/ context, as in "Input" "to air". This SEEMS WRONG.
    context: str


class Exchange(ResponseModel):
    """
    Do we need to add locale??
    """
    origin: str
    process: str
    flow: str
    direction: str
    termination: Optional[str]
    type: str  # {'reference', 'self', 'node', 'context', 'cutoff'}, per
    comment: Optional[str]
    str: str

    @classmethod
    def from_exchange(cls, x, **kwargs):
        if x.type == 'context':
            term = x.termination.name
        else:
            term = x.termination
        return cls(origin=x.process.origin, process=x.process.external_ref, flow=x.flow.external_ref,
                   direction=x.direction, termination=term, type=x.type, comment=x.comment, str=str(x), **kwargs)


class ReferenceExchange(Exchange):
    is_reference = True
    termination: None


class ReferenceValue(ReferenceExchange):
    value = float

    @classmethod
    def from_rx(cls, x):
        return cls.from_exchange(x, value=x.value)


class ExchangeValue(Exchange):
    """
    dict mapping reference flows to allocated value
    """
    values: Dict
    uncertainty: Optional[Dict]

    @classmethod
    def from_ev(cls, x):
        return cls.from_exchange(x, values=x.values)


class AllocatedExchange(Exchange):
    ref_flow: str
    value: float
    uncertainty: Optional[Dict]

    @classmethod
    def from_inv(cls, x, ref_flow:str):
        return cls.from_exchange(x, ref_flow=ref_flow, value=x.value)



def generate_pydantic_exchanges(xs, type=None):
    """

    :param xs: iterable of exchanges
    :param type: [None] whether to filter the exchanges by type. could be one of None, 'reference', 'self', 'node',
    'context', 'cutoff'
    :return:
    """
    for x in xs:
        if type and (type != x.type):
            continue
        if x.is_reference:
            yield ReferenceExchange.from_exchange(x)
            continue

        else:
            yield Exchange.from_exchange(x)


Exch_Modes = (None, 'reference', 'interior', 'exterior', 'cutoff')


def generate_pydantic_inventory(xs, mode=None, values=False, ref_flow=None):
    """
    Not currently used

    :param xs: iterable of exchanges
    :param mode: [None] whether to filter the exchanges by type. could be one of:
     None: generate all exchanges
     'interior'
     'exterior'
     'cutoff'
    :param values: (bool) [False] whether to include exchange values.
    :param ref_flow: (ignored if values=False) the reference flow with which the exchange value was computed. If None,
     this implies the exchange reports un-allocated exchange values
    :return:
    """
    if hasattr(ref_flow, 'entity_type'):
        if ref_flow.entity_type == 'flow':
            ref_flow = ref_flow.external_ref
        elif ref_flow.entity_type == 'exchange':
            ref_flow = ref_flow.flow.external_ref
        else:
            raise TypeError(ref_flow.entity_type)

    for x in xs:
        if x.is_reference:
            if mode and (mode != 'reference'):
                continue
            if values:
                yield ReferenceValue.from_rx(x)
            else:
                yield ReferenceExchange.from_exchange(x)
            continue

        else:
            if x.type in ('self', 'node'):
                if mode and (mode != 'interior'):
                    continue
            elif x.type in ('context', 'elementary'):
                if mode and (mode != 'exterior'):
                    continue
            elif x.type == 'cutoff':
                if mode and (mode != 'cutoff'):
                    continue

            yield AllocatedExchange.from_inv(x, ref_flow=ref_flow)


"""
Quantity Types
"""
class Characterization(ResponseModel):
    origin: str
    flowable: str
    ref_quantity: str
    ref_unit: str
    query_quantity: str
    query_unit: str
    context: List[str]
    value: Dict

    @classmethod
    def from_cf(cls, cf):
        ch = cls.null(cf)
        for loc in cf.locations:
            ch.value[loc] = cf[loc]
        return ch

    @classmethod
    def null(cls, cf):
        ch =  cls(origin=cf.origin, flowable=cf.flowable,
                  ref_quantity=cf.ref_quantity.external_ref, ref_unit=cf.ref_quantity.unit,
                  query_quantity=cf.quantity.external_ef, query_unit=cf.quantity.unit,
                  context=list(cf.context), value=dict())
        return ch


class Normalizations(ResponseModel):
    """
    This is written to replicate the normalisation data stored per-method in OpenLCA JSON-LD format
    """
    origin: str
    quantity: str
    norm: Dict
    weight: Dict

    @classmethod
    def from_q(cls, q):
        n = cls(origin=q.origin, quantity=q.external_ref, norm=dict(), weight=dict())
        if q.has_property('normSets'):
            sets = q['normSets']
            try:
                norms = q['normalisationFactors']
            except KeyError:
                norms = [0.0]*len(sets)
            try:
                wgts = q['weightingFactors']
            except KeyError:
                wgts = [0.0]*len(sets)
            for i, set in sets:
                n.norm[set] = norms[i]
                n.weight[set] = wgts[i]
        return n


class QuantityConversion(ResponseModel):
    """
    Technically, a quantity conversion can include chained QR Results, but we are flattening it (for now)
    """
    origin: str
    flowable: str
    ref_quantity: str
    query_quantity: str
    context: List[str]
    locale: str
    value: float

    @classmethod
    def from_qrresult(cls, qrr):
        return cls(origin=qrr.origin, flowable=qrr.flowable,
                   ref_quantity=qrr.ref.external_ref, query_quantity=qrr.query.external_ref,
                   context=list(qrr.context), locale=qrr.locale, value=qrr.value)

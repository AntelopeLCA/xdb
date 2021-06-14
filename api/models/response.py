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


class ReferenceExchange(ResponseModel):
    origin: str
    process: str
    flow: str
    direction: str
    comment: Optional[str]
    is_reference = True

    @classmethod
    def from_exchange(cls, x):
        return cls(origin=x.process.origin, process=x.process.external_ref, flow=x.flow.external_ref,
                   direction=x.direction, comment=x.comment)


class ReferenceValue(ReferenceExchange):
    value = float

    @classmethod
    def from_exchange(cls, x):
        return cls(origin=x.process.origin, process=x.process.external_ref, flow=x.flow.external_ref,
                   direction=x.direction, comment=x.comment, value=x.reference_value(x.flow))


class CutoffExchange(ReferenceExchange):
    termination: str = ''
    is_reference = False


class InteriorExchange(CutoffExchange):
    """
    Termination must be an external ref for a process
    """


class ExteriorExchange(CutoffExchange):
    """
    Termination must be a context-- if the context is elementary, then so is the exchange
    """



class CutoffExchangeValue(CutoffExchange):
    ref_flow: str
    value: float
    uncertainty: Optional[Dict]


class InteriorExchangeValue(InteriorExchange):
    ref_flow: str
    value: float
    uncertainty: Optional[Dict]


class ExteriorExchangeValue(ExteriorExchange):
    ref_flow: str
    value: float
    uncertainty: Optional[Dict]



def generate_pydantic_exchanges(xs, mode=None, values=False, ref_flow=None):
    """

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
                yield ReferenceValue.from_exchange(x)
            else:
                yield ReferenceExchange.from_exchange(x)
            continue

        xdict = {
            'origin': x.process.origin,
            'process': x.process.external_ref,
            'flow': x.flow.external_ref,
            'direction': x.direction,
            'comment': x.comment
        }
        if values:
            xdict.update(ref_flow=ref_flow, value=x.value)

        if x.type in ('self', 'node'):
            if mode and (mode != 'interior'):
                continue

            xdict['termination'] = x.termination
            if values:
                yield InteriorExchangeValue(**xdict)
            else:
                yield InteriorExchange(**xdict)

        elif x.type in ('context', 'elementary'):
            if mode and (mode != 'exterior'):
                continue

            xdict['termination'] = x.termination.name
            if values:
                yield ExteriorExchangeValue(**xdict)
            else:
                yield ExteriorExchange(**xdict)

        else:
            if mode and (mode != 'cutoff'):
                continue

            if values:
                yield CutoffExchangeValue(**xdict)
            else:
                yield CutoffExchange(**xdict)

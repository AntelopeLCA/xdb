"""
DEPRECATED-- these models now live in antelope_core
"""
from pydantic import BaseModel
from pydantic.typing import List
from antelope_core.models import QuantityConversion


class ServerMeta(BaseModel):
    title: str
    version: str
    description: str
    origins: List[str]
    authorized_origins: List[str]

    @classmethod
    def from_app(cls, app):
        obj = cls(title=app.title,
                  version=app.version,
                  description=app.description,
                  origins=list(),
                  authorized_origins=list())
        return obj


class QdbMeta(BaseModel):
    title: str
    description: str

    @classmethod
    def from_cat(cls, cat):
        lcia = cat.lcia_engine
        return cls(title=lcia.__class__.__name__, description="Antelope LCIA implementation")


class PostTerm(BaseModel):
    term: str


class PostFactors(BaseModel):
    """
    Client POSTs a list of FlowSpecs; server returns a list of characterizations that match the specs, grouped
    by flow external_ref (so as to be cached in the flow's chars_seen).

    The challenge here is with contexts: in order for lookup_cf to find the CF, it needs to be cached with a
    local context; but in order for the results to be portable/reproducible, the QR results should report the
    canonical contexts.  So, we add a context field where we reproduce the posted context.
    """
    flow_id: str
    context: List[str]
    factors: List[QuantityConversion]

    def add_qr_result(self, qrr):
        self.factors.append(QuantityConversion.from_qrresult(qrr))

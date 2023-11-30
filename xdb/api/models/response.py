"""
Non-server-specific models now live in the antelope interface
"""
from pydantic import BaseModel
from typing import List
from antelope.models import QuantityConversion
import pkg_resources

try:
    antelope_version = pkg_resources.require('antelope_interface')[0].version
except (ImportError, pkg_resources.DistributionNotFound):
    antelope_version = 'bleeding-dev'


class ServerMeta(BaseModel):
    title: str
    version: str
    antelope_version: str = antelope_version
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

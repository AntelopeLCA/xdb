# from etl import run_static_catalog, CAT_ROOT
import tempfile

from fastapi import HTTPException
from antelope.models import Entity, FlowEntity, Characterization
# from antelope_core.auth import AuthorizationGrant
from antelope_core.entities import MetaQuantityUnit
# from antelope_core.catalog import LcCatalog
from antelope_core.file_accessor import ResourceLoader

from .libs.xdb_catalog import XdbCatalog
from .libs.xdb_s3_sync import XdbS3Sync

# from antelope_manager.authorization import MASTER_ISSUER, open_public_key
import os
import logging


_ETYPES = ('processes', 'flows', 'quantities', 'lcia_methods', 'contexts')  # this should probably be an import


"""
UNRESTRICTED_GRANTS = [
    AuthorizationGrant(user='public', origin='lcacommons', access='index', values=True, update=False),
    AuthorizationGrant(user='public', origin='lcacommons', access='exchange', values=True, update=False),
    AuthorizationGrant(user='public', origin='lcacommons', access='background', values=True, update=False),
    AuthorizationGrant(user='public', origin='qdb', access='quantity', values=True, update=False),
    AuthorizationGrant(user='public', origin='openlca', access='index', values=True, update=False),
    AuthorizationGrant(user='public', origin='openlca', access='quantity', values=True, update=False),
]


PUBLIC_ORIGINS = list(set(k.origin for k in UNRESTRICTED_GRANTS))


cat = run_static_catalog(CAT_ROOT, list(PUBLIC_ORIGINS))
"""

# these must be specified at instantiation-- specified by the blackbook server
MASTER_ISSUER = os.getenv('MASTER_ISSUER')
CAT_ROOT = os.getenv('XDB_CATALOG_ROOT')
if CAT_ROOT is None:
    # this really doesn't work because the tempdir could never have the PUBKEYS stored.
    CAT_ROOT = tempfile.TemporaryDirectory().name

DATA_ROOT = os.path.abspath(os.getenv('XDB_DATA_ROOT'))
DATA_AWS_BUCKET = 'antelope-data'


def lca_init():
    _cat = XdbCatalog(CAT_ROOT, strict_clookup=False)
    # do config here

    return _cat


cat = lca_init()


def _aws_sync_origin(origin):
    s3_client = XdbS3Sync(DATA_AWS_BUCKET)

    target_dir = os.path.join(DATA_ROOT, origin)
    os.makedirs(target_dir, exist_ok=True)

    logging.info('Pulling origin %s from S3 into %s' % (origin, DATA_ROOT))
    s3_client.retrieve_s3_folder(origin, DATA_ROOT)


def init_origin(origin, reset=False):
    """
    Remove any resources associated with the origin first
    then sync the
    Use ResourceLoader to install resources from the named directory into the catalog
    :param origin:
    :param reset: [False] if true, delete the resources and start over
    :return:
    """
    if reset:
        cat.reset_origin(origin)
        _aws_sync_origin(origin)
    elif not os.path.exists(os.path.join(DATA_ROOT, origin)):
        _aws_sync_origin(origin)
    rl = ResourceLoader(DATA_ROOT)
    return rl.load_resources(cat, origin, check=True)


def search_entities(query, etype, count=50, **kwargs):
    sargs = {k: v for k, v in filter(lambda x: x[1] is not None, kwargs.items())}
    if etype not in _ETYPES:
        raise HTTPException(404, "Invalid entity type %s" % etype)
    logging.info('search origin %s/%s ' % (query.origin, etype))
    for k, v in sargs.items():
        logging.info('search item |%s|%s|' % (k, v))
    try:
        it = getattr(query, etype)(**sargs)
    except AttributeError:
        raise HTTPException(404, "Unknown entity type %s" % etype)
    sargs.pop('unit', None)  # special arg that gets passed to quantity method but does not work as a property
    for e in it:
        if not e.origin.startswith(query.origin):  # return more-specific
            continue
        if etype == 'flows':
            yield FlowEntity.from_flow(e, **sargs)
        else:
            yield Entity.from_entity(e, **sargs)
        count -= 1
        if count <= 0:
            break


def do_lcia(query, qq, lci, **kwargs):
    if qq.unit == MetaQuantityUnit.unitstring and qq.has_property('impactCategories'):
        qs = [query.get_canonical(k) for k in qq['impactCategories']]
    else:
        qs = [qq]

    # check authorization for detailed Lcia
    return [q.do_lcia(lci, **kwargs) for q in qs]


def canonical_cf(cf):
    context = list(cat.lcia_engine[cf.context])
    ch = Characterization(origin=cf.origin, flowable=cf.flowable,
                          ref_quantity=cf.ref_quantity.external_ref, ref_unit=cf.ref_quantity.unit,
                          query_quantity=cf.quantity.external_ref, query_unit=cf.quantity.unit,
                          context=context, value=dict())
    for loc in cf.locations:
        ch.value[loc] = cf[loc]
    return ch



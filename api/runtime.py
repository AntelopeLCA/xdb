from etl import run_static_catalog, CONFIG_ORIGINS, CAT_ROOT
from fastapi import HTTPException
from antelope_core.models import Entity, FlowEntity, UnallocatedExchange
from antelope_core.entities import MetaQuantityUnit


_ETYPES = ('processes', 'flows', 'quantities', 'lcia_methods', 'contexts')  # this should probably be an import

cat = run_static_catalog(CAT_ROOT, list(CONFIG_ORIGINS))




def search_entities(query, etype, count=50, **kwargs):
    sargs = {k:v for k, v in filter(lambda x: x[1] is not None, kwargs.items())}
    if etype not in _ETYPES:
        raise HTTPException(404, "Invalid entity type %s" % etype)
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


def do_lcia(query, qq, lci, locale=None):
    if qq.unit == MetaQuantityUnit.unitstring and qq.has_property('impactCategories'):
        qs = [query.get(k) for k in qq['impactCategories']]
    else:
        qs = [qq]

    # check authorization for detailed Lcia
    return [q.do_lcia(lci, locale=locale) for q in qs]

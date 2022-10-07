from .xdb_catalog import XdbCatalog


def run_static_catalog(cat_root):
    s_cat = XdbCatalog(cat_root, strict_clookup=False)

    return s_cat  # use this to answer all HTTP queries

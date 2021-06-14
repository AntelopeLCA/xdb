from antelope_core.catalog import StaticCatalog
from dagster import solid, InputDefinition, OutputDefinition, String, List


@solid(input_defs=[InputDefinition(name="cat_root",dagster_type=String), InputDefinition(name="config_origins", dagster_type=List[String])],
       output_defs=[OutputDefinition(name="s_cat", dagster_type=StaticCatalog)])


def run_static_catalog(cat_root, config_origins):
    s_cat = StaticCatalog(cat_root)
    for origin in config_origins:
        for iface in('exchange', 'index', 'background'):
            assert ':'.join([origin, iface]) in s_cat.interfaces

    return s_cat  # use this to answer all HTTP queries

from antelope_core.catalog import LcCatalog
from antelope_core.file_accessor import ResourceLoader
from dagster import solid, InputDefinition, OutputDefinition, String, List


@solid(input_defs=[InputDefinition(name="data_root", dagster_type=String), InputDefinition(name="cat_root",dagster_type=String)],
       output_defs=[OutputDefinition(name="statuses", dagster_type=List)])
def construct_container_catalog(context, data_root, cat_root):
    cat = LcCatalog(cat_root)
    ars = ResourceLoader(data_root)
    return ars.load_resources(cat)

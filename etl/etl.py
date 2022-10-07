"""
This whole file is cruft

from dagster import pipeline, repository, PresetDefinition, ModeDefinition, fs_io_manager, file_relative_path
from etl.solids.sync_data import sync_data

mode_defs   = [ModeDefinition(resource_defs={"io_manager":fs_io_manager})]

preset_defs = [ PresetDefinition.from_files(name="full", config_files=[file_relative_path(__file__, "config/full.yaml")]),
              PresetDefinition.from_files(name="partial", config_files=[file_relative_path(__file__, "config/partial.yaml")])]

@pipeline(mode_defs=mode_defs, preset_defs=preset_defs)
def data_pipeline():
    sync_data()

@repository
def xdb():
    return [
        data_pipeline
    ]

"""
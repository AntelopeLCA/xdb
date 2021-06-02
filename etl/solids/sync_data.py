import os
from dagster import solid, InputDefinition, OutputDefinition, String

#
# Data Sync s3://antelope-data or s3://antelope-data-fixture
#

@solid(input_defs=[InputDefinition(name="bucket", dagster_type=String), InputDefinition(name="data_path",dagster_type=String)],
       output_defs=[OutputDefinition(name="data_path", dagster_type=String)])

def sync_data(context, bucket, data_path):
    os.system(f"aws s3 sync s3://{bucket} {data_path} > /project/etl/s3-logs")
    return data_path
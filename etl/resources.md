# Data Resources

An antelope catalog acts as an intermediary between information queries and data resources.  Each data resource 
is assigned an "origin" which describes in an intelligible, hierarchical way the authority that is responsible for
the data.  Each query belongs to a particular sub-interface that allows different implementations to be used for
different types of data.  The role of the catalog is to map the query to the resource that can answer it.

When a catalog starts up, it has only one resource: a local quantity database or `qdb`.  Resources are added to the 
catalog during initialization.  The challenge is in specifying those resources at load time.

## Using S3

The current plan is to store data resources on S3, and then sync those files over to a container when it is 
initialized.  The data structure on S3 is as follows:

    s3://antelope-data/qdb                                                -- qdb-specific content
    s3://antelope-data/[origin]/[interface]/config.json                   -- configuration info
    s3://antelope-data/[origin]/[interface]/[provider type]/[source]      -- the data source
    
The container configuration will provide a list of `origins`; for each origin the container initializer should execute 
`aws s3 sync s3://antelope-data/[origin] /aws-data/[origin]`, thus copying the remote data to the container.

Subsequently, the ETL routine should crawl the `aws-data` directory 
# Data Resources

An antelope catalog acts as an intermediary between information queries and data resources.  Each data resource 
is assigned an "origin" which describes in an intelligible, hierarchical way the authority that is responsible for
the data.  Each query belongs to a particular sub-interface that allows different implementations to be used for
different types of data.  The role of the catalog is to map the query to the resource that can answer it.

When a catalog starts up, it has only one resource: a local quantity database or `qdb`.  Resources are added to the 
catalog during initialization.  The challenge is in specifying those resources at load time.

## The proper way

The best way to create RESTful containers for serving reference content is to make them static.  We already have a 
class, `StaticCatalog`, that was created for the purpose of disallowing configuration changes.  So we use it as 
designed: we create an `LcCatalog`, assign resources to it, and then open a static catalog to back the HTTP server.

The assigning resources can all be done in advance, as part of ETL.  The products of the ETL process include:

 - ensure persistent index and background files on s3 for a list of configured origins
 - create a catalog root directory populated with resources
 
The catalog root directory is used as the input to the `StaticCatalog` server that answers all runtime queries.

In the future, we will no longer have local index files;  instead just a resource pointing to a remote antelope 
server running on top of a proper database.   `qdb` is also an antelope server with a different set of routes 
(defaults to catalog's own local.qdb)

## Creating persistent content

 * We create a background engine container that (as envisioned) is given an ecoinvent 7z or a uslci olca zip, 
 indexes it, orders it, writes index to [json or remote persistent store] and saves the background
 
 * This background engine then writes the result files to the s3 store 
 
 * It opens a catalog

## Using S3

The current plan is to store data resources on S3, and then sync those files over to a container when it is 
initialized.  The data structure on S3 follows the REST API to one level down:

    s3://antelope-data/qdb                                                -- qdb-specific content
    s3://antelope-data/[origin]/[interface]/[provider type]/config.json   -- configuration info
    s3://antelope-data/[origin]/[interface]/[provider type]/[source]      -- the data source
    
The container configuration will provide a list of `origins`; for each origin the container initializer should 
execute `aws s3 sync s3://antelope-data/[origin] /aws-data/[origin]`, thus copying the remote data to the container.
For 7z files, unfortunately they must be expanded because accessing zipped content is buggy in `pylzma`.  Once
expanded, the 7z files themselves should be removed to prevent double-loading.

Subsequently, the ETL routine should run the `AwsFileCrawler` to generate resources on a designated catalog root.

Then  
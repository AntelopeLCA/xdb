# xdb
Exchange database

This repo contains a deployable antelope server that is exposed via a REST API. All the exchange data are static, so a REST model is appropriate.

The server should be linked to an authentication and authorization mechanism that would evaluate each request in terms of the requestor's access level.

## config

The default initialized xdb server runs a standard `LcCatalog` with a local qdb.  Resources are added to the catalog through etl.  A default self-standing initialization would:

 - Instantiate the catalog and http server
 - add an exchange resource, specified by (origin)/(interface)
 - obtain or create an index resource for the specified origin
 - check_bg for the specified origin
 - publish the resource

## API spec

See [api/antelope_api.md](api/antelope_api.md)


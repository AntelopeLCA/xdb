# xdb
Antelope Exchange database

This is a REST HTTP server for hosting LCA data according to the [Antelope interface](https://github.com/AntelopeLCA/antelope).
 This repo contains a deployable antelope server that is exposed via a REST API. All the exchange data are static, so a REST model is appropriate.

The server is linked to an authentication and authorization mechanism that would evaluate each request in terms of the requester's access level.
Every query must be accompanied by an authorization token that has been computed as indicated in
[xdb_tokens.py](https://github.com/AntelopeLCA/antelope/blob/virtualize/antelope/xdb_tokens.py).



## Run the server

The 
From the root directory, run:

    $ ANTELOPE_CATALOG_ROOT=/data/LCI/my_container uvicorn api:app --host 0.0.0.0 --reload
    


## config

The default initialized xdb server runs a standard `LcCatalog` with a local qdb.  Resources are added to the catalog through etl.  A default self-standing initialization would:

 - Instantiate the catalog and http server
 - add an exchange resource, specified by (origin)/(interface)
 - obtain or create an index resource for the specified origin
 - check_bg for the specified origin
 - publish the resource

## API spec

See [api/antelope_api.md](api/antelope_api.md)


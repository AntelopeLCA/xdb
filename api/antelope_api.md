# Antelope API

Ostensibly, antelope v1 was the CalRecycle / ASP.NET / uo-lca implementation, with unit-indexed entities.

antelope v2 was first operationalized with amaru, and this is rewriting that.

## Query Design

Antelope implements a number of sub-interfaces for describing and accessing LCA data.  Each sub-interface is defined by a set of REST query routes.  The set of routes can be summarized as follows:

    <set of operations>
    [set of values]

    APIv2_ROOT/<server-wide queries>
    APIv2_ROOT/[origin]/<index queries>
    APIv2_ROOT/[origin]/[entity id]/<entity queries>
    APIv2_ROOT/[origin]/[entity id]/doc/<documentation queries>

Entity queries include index, exchange, and background (lci) queries.

### Origins and public names

 - `origin`
 - `entity id`

Data are assigned to sets of *entities*, which are defined with respect to various semantic / curated *origins*.  An example origin could be "ecoinvent" or "uslci".  They are meant to represent broadly understood and agreed-upon sources of authoritative information.

The `origin` in the query is meant to be hieararchically differentiated, so (for instance) `ecoinvent.3.4.cutoff` is differentiated from `ecoinvent.3.7.1.consequential` in an unambiguous (and hopefully discoverable) way.  

A tuple of (origin, external reference) specifies a distinct entity.  In the event of an incompletely or ambiguously specified origin, the catalog will attempt to return the first-best result found in known sub-origins, according to a prioritization that can be set by the data publisher.

### server-wide queries

    APIv2_ROOT/origins             - return list of known origins

these are not really server-wide, except for qdb, which is a different server:

    APIv2_ROOT/flowables	   - list flowables; query to search
    APIv2_ROOT/synonyms/[term]     - list synonyms for the specified term
    APIv2_ROOT/synonyms?term=term  -  "" ""

### Index queries

Origin-specific queries:

    APIv2_ROOT/[origin]/<entities>  - list entities; query to search
    APIv2_ROOT/[origin]/processes
    APIv2_ROOT/[origin]/flows
    APIv2_ROOT/[origin]/quantities
    APIv2_ROOT/[origin]/contexts
    APIv2_ROOT/[origin]/flowables

    APIv2_ROOT/[origin]/count	           - count of all entity types
    APIv2_ROOT/[origin]/count/<entityies>  - count of specified entity type
    APIv2_ROOT/[origin]/count/processes
    APIv2_ROOT/[origin]/count/flows
    APIv2_ROOT/[origin]/count/quantities
    APIv2_ROOT/[origin]/count/contexts
    APIv2_ROOT/[origin]/count/flowables

    APIv2_ROOT/[origin]/synonyms/[term]       - list synonyms for the specified term
    APIv2_ROOT/[origin]/synonyms?term=term    -  ""  ""
    APIv2_ROOT/[origin]/get_context/[term]    - return canonical context name for term
    APIv2_ROOT/[origin]/get_context?term=term -  ""  ""

Entity-specific queries:

    APIv2_ROOT/[origin]/[entity id]/reference   - return a unitary reference*
    APIv2_ROOT/[origin]/[process id]/references - return list of reference exchanges
    APIv2_ROOT/[origin]/[flow id]/targets       - return reference exchanges containing the flow

* Processes are constituted to have zero or more reference exchanges, though most have only one.  If a process has a single reference exchange (or if a unitary reference is somehow designated), it will be returned; otherwise a 404 is returned with the message "Multiple References".

On the other hand, non-processes with unitary references can always be returned as single-entry lists, so the `references` query will never return an error for a valid entity.

### Documentary queries

Part of the point of antelope is to operationalize access to metadata.

    APIv2_ROOT/[origin]/properties  		   - return complete set of all properties known
    APIv2_ROOT/[origin]/[entity id]                - return a thorough description of the entity
    APIv2_ROOT/[origin]/[entity id]/doc		   - return an auto-generated entity doc page 
    APIv2_ROOT/[origin]/[entity id]/properties     - return a list of properties defined for entity
    APIv2_ROOT/[origin]/[entity id]/doc/properties -   ""  ""
    APIv2_ROOT/[origin]/[entity id]/doc/[property] - get the specified property

Somewhere in here is a smart, adaptive semantic mapping between REST-queryable routes and the universes of ecospold, ILCD, openlca, and other data serialization formats.

Documentary information could in principle be POSTed or PUT, if the client has the appropriate permission.

### Exchange queries

All exchange queries are entity (process)-specific, and each can take the query parameters `direction` and `termination`.  Direction is either `Input` or `Output` (or something that translates to that).  Termination can be either a recognized context (w.r.t. the origin) or the entity ID of the exchange's terminal node.

The willingness of the server to answer `exchange`, `exchange_value`, and `ev` queries must be determined based on the query's authentication / scope of authorization and subject to data provider's policy.  

    APIv2_ROOT/[origin]/[process id]/exchanges?...
    APIv2_ROOT/[origin]/[process id]/exchanges/[flow_id]?...

    APIv2_ROOT/[origin]/[process id]/exchange_values?...
    APIv2_ROOT/[origin]/[process id]/exchange_values/[flow_id]?...
    APIv2_ROOT/[origin]/[process id]/exchange_values/[ref id]/[flow id]?...

    APIv2_ROOT/[origin]/[process id]/ev/[flow id]?...
    APIv2_ROOT/[origin]/[process id]/ev/[ref id]/[flow id]?...

The first route `exchanges` returns qualitative exchanges only, without numerical data [but including terminations].

The next route `exchange_values` returns exchanges with numerical exchange values.  The interpretation of the exchange values is complex and depends on the process's set of reference exchanges.

If the process has no designated references, then the exact values are returned.

If the process has one designated reference, then the values are returned after being normalized to that reference's exchange value.

If the process has multiple reference exchanges, the query must take the form in which the desired reference is specified (by flow ID of the reference exchange).  In this case, the exchange value is normalized by the specified reference's exchange value and returned.

If the process has multiple reference exchanges, and the query does not specify one, then the query is requesting an un-allocated exchange value-- this may not be known (404), or else sharing it may be inconsistent with the data provider's policy (403).  Or else the request will be granted.

The final route, `ev`, always returns a single float, which is the sum of the exchange values returned from the corresponding `exchange_values` query.

    APIv2_ROOT/[origin]/[process id]/inventory
    APIv2_ROOT/[origin]/[process id]/inventory/[ref id]

The `inventory` routes are similar to the `exchange_values` routes- when no reference is specified, the route returns all (reference and non-reference) un-normalized, un-allocated exchange values if known or permitted.  When a reference exchange is specified, the route returns non-reference exchanges only, normalized to the specified reference.

### Background / LCI queries

These queries depend on the construction of "interior" (approximating the "technology" or *A* matrix) and "exterior" (the *B* matrix) matrices from the processes present in the origin.  All exchanges that can be terminated to a process are considered "interior"; all exchanges terminated to contexts, plus all exchanges for which no targets are found, are considered "exterior".  The processes are partially-ordered; this ordering is used to distinguish "foreground" from "background" processes.

    APIv2_ROOT/[origin]/foreground   - [reference exchanges]
    APIv2_ROOT/[origin]/background   - [reference exchanges]
    APIv2_ROOT/[origin]/interior     - [reference exchanges]
    APIv2_ROOT/[origin]/exterior     - [exterior flows]

Aspects depending on the topological position of specific products can be queried directly, but in general both the process ID and the ID of the reference exchange must be specified:

    APIv2_ROOT/[origin]/[process id]/[ref flow]/<aspects>

Only in cases where processes have a single designated reference exchange, may the [ref flow] specification be omitted (processes with no reference exchanges cannot be ordered):

    APIv2_ROOT/[origin]/[process id]/<aspects>

All background aspect queries return lists of exchanges, either reference exchanges (value always 1) or dependent exchanges (normalized to reference exchange).  The "aspects" are as follows:

    APIv2_ROOT/[origin]/[process id]/[ref flow]/consumers	- [reference exchanges]
    APIv2_ROOT/[origin]/[process id]/[ref flow]/dependencies	- [exchange values]
    APIv2_ROOT/[origin]/[process id]/[ref flow]/emissions	- [exchange values]
    APIv2_ROOT/[origin]/[process id]/[ref flow]/cutoffs		- [exchange values]
    APIv2_ROOT/[origin]/[process id]/[ref flow]/lci		- [exchange values]
    APIv2_ROOT/[origin]/[process id]/[ref flow]/sys_lci		- [exchange values]	
    APIv2_ROOT/[origin]/[process id]/[ref flow]/foreground	- [exchange values]
    APIv2_ROOT/[origin]/[process id]/[ref flow]/ad		- [exchange values]
    APIv2_ROOT/[origin]/[process id]/[ref flow]/bf		- [exchange values]

Only flows terminated to *elementary* contexts are emissions; other flows (both unterminated and terminated to intermediate contexts) are "cutoffs".

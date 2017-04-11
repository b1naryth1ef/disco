# Client

Generally, almost all interactions through Disco will utilize some form of the Disco client. The client is an abstraction over the multiple transport and API protocols used to communicate with Discord, and it also includes utilities for tracking and caching real-time state. Most users will not want to construct an instance of the client themselves, but rather utilize one of Disco's helper facets (such as a Bot) that further wrap and abstract the client.


## API

### ClientConfig

Object used to configure the basic behavior and functionality of the client.

#### Attributes

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| token | string | The Discord authentication token | `""` |
| shard\_id | integer | The shard ID for this instance | `0` |
| shard\_count | integer | The total number of shards | `1` |
| max\_reconnects | integer | The maxmium number of reconnects (not resumes) to attempt before giving up | `5` |
| manhole\_enable | boolean | Whether the manhole server is enabled | `False` |
| manhole\_bind | tuple(string, integer) | The bind information for the manhole server | `('127.0.0.1', 8484)` |


### Client

Class representing the base abstraction point of Disco.

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| config | `ClientConfig` | The configuration for this client instance |

#### Attributes

| Field | Type | Description |
|-------|------|-------------|
| config | `ClientConfig` | The configuration for this client instance |
| events | `holster.emitter.Emitter` | 

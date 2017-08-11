# CHANGELOG

## v0.0.12

### Fixes

- Fixed `Paginator` throwing an exception when reaching the end of pagination, instead of just ending its iteration

## v0.0.11

### Additions

- Added support for Guild audit logs, exposed via `Guild.get_audit_log_entries`, `Guild.audit_log` and `Guild.audit_log_iter`. For more information see the `AuditLogEntry` model
- Added built-in Flask HTTP server which can be enabled via `http_enabled` and configured via `http_host`/`http_port` config options. The server allows plugins to define routes which can be called externally.
- Added support for capturing the raw responses returned from API requests via the `APIClient.capture` contextmanager
- Added support for NSFW channels via `Channel.nsfw` and `Channel.is_nsfw`
- Added initial support for channel categories via `Channel.parent_id` and `Channel.parent`
- Added various setters for updating Channel properties, e.g. `Channel.set_topic`
- Added support for audit log reasons, accessible through passing `reason` to various methods
- Added `disco.util.snowflake.from_timestamp_ms`
- Added support for `on_complete` callback within DCADOpusEncoderPlayable
- **BREAKING** Added new custom queue types `BaseQueue`/`PlayableQueue` for use w/ `Player`.
  - `queue` can be passed when creating a `Player`, should inherit from BaseQueue
  - Users who previously utilized the `put` method of the old `Player.queue` must move to using `Player.queue.append`, or providing a custom queue implementation.
- Added `Emoji.custom` property

### Fixes

- Fixed GuildRoleCreate missing guild\_id, resulting in incorrect state
- Fixed SimpleLimiter behaving incorrectly (causing GW socket to be ratelimited in some cases)
- Fixed the shortest possible match for a single command being an empty string
- Fixed group matching being overly greedy, which allowed for extra characters to be allowed at the end of a group match
- Fixed errors thrown when not enabling manhole via cli
- Fixed various warnings emitted due to useage of StopIteration
- Fixed warnings about missing voice libs when importing `disco.types.channel`
- Fixed `Bot.get_commands_for_message` returning None (instead of empty list) in some cases

### Etc

- Greatly imrpoved the performance of `HashMap`
- **BREAKING** Increased the weight of group matches over command argument matches, and limited the number of commands executed per message to one.
- Reuse a buffer in voice code to slightly improve performance

## v0.0.11-rc.8

### Additions

- Added support for capturing the raw responses returned from the API via `APIClient.capture` contextmanager
- Added various pieces of documentation

### Fixes

- Fixed Python 3 errors and Python 2 deprecation warnings for CommandError using `.message` attribute

### ETC

- Grealty improved the performance of the custom HashMap
- Moved tests around and added pytest as the testing framework of choice


## v0.0.11-rc.7

### Additions

- Added support for new NSFW attribute of channels
  - `Channel.nsfw`
  - `Channel.set_nsfw`
  - `Channel.is_nsfw` behaves correctly, checking both the deprecated `nsfw-` prefix and the new attribute
- Added support for `on_complete` callback within DCADOpusEncoderPlayable
- **BREAKING** Added new custom queue types `BaseQueue`/`PlayableQueue` for use w/ `Player`.
  - `queue` can be passed when creating a `Player`, should inherit from BaseQueue
  - Users who previously utilized the `put` method of the old `Player.queue` must move to using `Player.queue.append`, or providing a custom queue implementation.

### Fixes

- Fixed bug within SimpleLimiter which would cause all events after a quiescent period to be immedietly dispatched. This would cause gateway disconnects w/ RATE\_LIMITED on clients with many Guilds and member sync enabled.

### ETC

- Improved log messages within GatewayClient
- Log voice endpoint within VoiceClient

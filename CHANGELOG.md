# CHANGELOG

## v0.0.12

### Additions

- **MAJOR** Added voice gateway v3 support. This will result in increased stability for voice connections
- **BREAKING** Updated holster to v2.0.0 which changes the way emitters work (and removes the previous priorities). A migration guide will be provided post-RC cycle.
- Added support for ETF on Python 3.x via `earl-etf` (@GiovanniMCMXCIX)
- Supported detecting dead/inactive/zombied Gateway websocket connections via tracking `HEARTBEAT_ACK` (@PixeLInc)
- Added support for animated emoji (@Seklfreak)
- Added support for `LISTENING` and `WATCHING` game statuses (@PixeLInc)
- Added `wsaccel` package within the `performance` pack, should improve websocket performance
- Added the concept of a `shared_config` which propgates its options to all plugin configs (@enkoder)
- Added support for streaming zlib compression to our gateway socket. This is enabled by default and provides significant performance improvements on startup and overall bandwidth usage
- Added support for `Guild.system_channel_id` and `GUILD_MEMBER_JOIN` system message
- Added `Guild.create_category`, `Guild.create_text_channel` and `Guild.create_voice_channel`
- Added `Channel.create_text_channel` and `Channel.create_voice_channel` which can be called only on category channels to add sub-channels

### Fixes

- Fixed 'Invalid token passed' errors from showing up (via removal of token validation)
- Fixed `IndexError` being raised when `MessageIterator` was done iterating (@Majora320)
- Fixed overwrite calculations in `Channel.get_permissions` (@cookkkie)
- A plethora of PEP8 and general syntax changes have been made to cleanup the code
- Fixed a bug with `Emoji.custom`
- Fixed a bug in the typing system that would not allow Field's to have a `default` of `None`
- Fixed the `__str__` method for Channel's displaying (useless) unset data for DMs
- Fixed a bug with `MessageIterator` related to iterating before or after an ID of 0
- Fixed incorrect field name (`icon_proxy_url` vs `proxy_icon_url`) in MessageEmbedAuthor model
- Fixed bugs related to creating and deleting pinned messages
- Fixed `GuildBan.reason` incorrectly handling unicode reasons
- Fixed `Paginator` throwing an exception when reaching the end of pagination, instead of just ending its iteration
- Fixed `Paginator` defaulting to start at 0 for all iterations

### Etc

- **BREAKING** Refactor the way Role's are managed and updated. You should update your code to use `Role.update`
- **BREAKING** Renamed `Model.update` to `Model.inplace_update`. You should not have to worry about this change unless you explicitly call that method
- **DEPRECATION** Deprecated the use of `Guild.create_channel`. You should use the explicit channel type creation methods added in this release
- Cleaned up various documentation
- Removed some outdated storage/etc examples
- Expanded `APIClient.guilds_roles_create` to handle more attributes
- Bumped various requirement versions

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

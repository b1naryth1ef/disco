# CHANGELOG

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

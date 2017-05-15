# disco
Disco is a simple and extendable library for the [Discord API](https://discordapp.com/developers/docs/intro). Join the Official channel and chat [here](https://discord.gg/XJRZSQk).

- Expressive, functional interface that gets out of the way
- Built for high-performance and efficiency
- Configurable and modular, take the bits you need
- Full support for Python 2.x/3.x
- Evented networking and IO using Gevent

## WARNING

Disco is currently in an early-alpha phase. What you see today may change a lot tomorrow. If you are looking to build a serious bot with this, wait for a stable release.

## Installation

Disco was built to run both as a generic-use library, and a standalone bot toolkit. Installing disco is as easy as running `pip install disco-py`, however some extra packages are recommended for power-users, namely:

|Name|Reason|
|----|------|
|requests[security]|adds packages for a proper SSL implementation|
|ujson|faster json parser, improves performance|
|erlpack|ETF parser, only Python 2.x, run with the --encoder=etf flag|
|gipc|Gevent IPC, required for autosharding|

## Examples

Simple bot using the builtin bot authoring tools:

```python
from disco.bot import Bot, Plugin


class SimplePlugin(Plugin):
    # Plugins provide an easy interface for listening to Discord events
    @Plugin.listen('ChannelCreate')
    def on_channel_create(self, event):
        event.channel.send_message('Woah, a new channel huh!')

    # They also provide an easy-to-use command component
    @Plugin.command('ping')
    def on_ping_command(self, event):
        event.msg.reply('Pong!')

    # Which includes command argument parsing
    @Plugin.command('echo', '<content:str...>')
    def on_echo_command(self, event, content):
        event.msg.reply(content)
```

Using the default bot configuration, we can now run this script like so:

`python -m disco.cli --token="MY_DISCORD_TOKEN" --run-bot --plugin simpleplugin`

And commands can be triggered by mentioning the bot (configured by the BotConfig.command\_require\_mention flag):

![](http://i.imgur.com/Vw6T8bi.png)

# disco
Disco is a simple and extendable library for the [Discord API](https://discordapp.com/developers/docs/intro).

- Expressive, functional interface that gets out of the way
- Built for high-performance and efficiency
- Configurable and modular, take the bits you need
- Full support for Python 2.x/3.x
- Evented networking and IO using Gevent

## Installation

Disco was built to run both as a generic-use library, and a standalone bot toolkit. Installing disco is as easy as running `pip install disco`, however some extra packages are recommended for power-users, namely:

|Name|Reason|
|----|------|
|requests[security]|adds packages for a proper SSL implementation|
|rapidjson|provides a Python implementation of the C rapidjson library, improves performance|

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

if __name__ == '__main__':
    Bot.from_cli(
        SimplePlugin
    ).run_forever()
```

Using the default bot configuration, we can now run this script like so:

`./simple.py --token="MY_DISCORD_TOKEN"`

And commands can be triggered by mentioning the bot (configued by the BotConfig.command\_require\_mention flag):

![](http://i.imgur.com/Vw6T8bi.png)

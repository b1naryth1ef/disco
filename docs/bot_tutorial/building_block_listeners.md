# Listeners
Listeners are a way to execute custom actions when a certain Discord event happens. For example, on message creation, when a member joins or leaves a guild, or when someone changes their username or nickname.

## Listeners in disco
Listeners are easy to use and implement in Disco. First of all, we'll create a [Plugin](https://b1naryth1ef.github.io/disco/bot_tutorial/building_block_plugins.html) like so:
```py
class MyPlugin(Plugin):
```
Now, inside this plugin, we'll create our first listener. A listener is built up following this syntax:
```py
@Plugin.listen('EventName')
def on_event_name(self, event):
    # Do something with the event
```
Change the `'EventName'` in the `.listen()` method to the event name you want to listen to, and give the `on_event_name` method a more descriptive name.

This listener will listen for a new message and will reply with the exact same message every time. 
```py
@Plugin.listen('MesageCreate')
def on_message_create(self, event):
    event.reply(event.message.content)
```
Let's create another listener, this time one that listens for a member that's added to the guild, when this happens, it will send a welcome message in a welcome channel:
```py
WELCOME_CHANNEL = 381890676654080001

@Plugin.listen('GuildMemberAdd')
def on_member_add(self, event):
    self.bot.client.state.channels.get(WELCOME_CHANNEL).send_message(
        'Welcome to the server {}'.format(event.member.user.mention())
    )
```

A list of all Discord events supported by disco can be found [here](https://b1naryth1ef.github.io/disco/api/disco_gateway_events.html) including event attributes and functions you can use on the event property.

These are all the listeners we created in this tutorial:

```py
class MyPlugin(Plugin):
    @Plugin.listen('MesageCreate')
    def on_message_create(self, event):
        event.reply(event.message.content)
    
    WELCOME_CHANNEL = 381890676654080001

    @Plugin.listen('GuildMemberAdd')
    def on_member_add(self, event):
        self.bot.client.state.channels.get(WELCOME_CHANNEL).send_message(
            'Welcome to the server {}'.format(event.member.user.mention())
        )
```

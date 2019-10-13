# Listeners

Listeners provide an API to listen to and execute code upon the occurrence of specified Discord events.

## Listener Basics

To start off with, lets create a listener attached to our plugin that fires whenever a message is created.

```py
@Plugin.listen('MessageCreate')
def on_message_create(self, event):
    self.log.debug('Got message: %s', event.message)
```

Ok, but what if we want to make a listener which welcomes new users to our server? Well that's also easy:

```py
@Plugin.listen('GuildMemberAdd')
def on_guild_member_add(self, event):
    self.state.channels.get(MY_WELCOME_CHANNEL_ID).send_message(
        'Hey there {}, welcome to the server!'.format(event.member.mention)
    )
```

## Listener Events

To see all the events you can subscribe too, checkout the [gateway events list](https://b1naryth1ef.github.io/disco/api/disco_gateway_events.html).

## Listener Priority

Each listener that's registered comes with a priority. This priority describes how the builtin event emitter will distribute events to your listener. To set a priority you can simply pass the priority kwarg:

```py
from disco.util.emitter import Priority

@Plugin.listen('GuildMemberAdd', priority=Priority.BEFORE)
def on_guild_member_add(self, event):
    # This would be very bad, don't do this...
    time.sleep(10)
```

#### Priorities

| Name | Description |
|------|-------------|
| BEFORE | Receives all events sequentially alongside the emitter. This is the most dangerous priority level, as any executed code will block other events in the emitter from flowing. Blocking within a BEFORE handler can be lethal. |
| SEQUENTIAL | Receives all events sequentially, but within a separate greenlet. This priority level can be used for plugins that require sequential events but may block or take a long time to execute their event handler. |
| NONE | This priority provides no guarantees about the ordering of events. Similar to SEQUENTIAL all event handlers are called within a separate greenlet. |

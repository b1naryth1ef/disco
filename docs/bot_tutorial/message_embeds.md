# Message Embeds

A [Message Embed](https://b1naryth1ef.github.io/disco/api/disco_types_message.html#messageembed) represents a Discord Embed object. An Embed object is another component of Discord messages that can be used to present data with special formatting and structure.

An example of a message embed: 

![A discord embed](https://i.stack.imgur.com/HRWHk.png "A discord embed")

An embed can contain the following components:
* Author, including link and avatar
* Title
* Description
* Field(s)
* Thumbnail image
* Image
* Footer, including text and icon
* Timestamp
* Color (sets the color of the left sidebar of the embed)

## Creating an embed
Creating an embed is simple, and can be done like this:
```py
from disco.types.message import MessageEmbed #We need this to create the embed
from datetime import datetime #We need this to set the timestamp

embed = MessageEmbed()
```
This will create a default, empty, Discord Embed object. Now that we have that, let's assign some values to it. First, lets set the author and the title, with a link that leads to this page. This can be done as follows:
```py
embed.set_author(name='b1nzy#1337', url='https://b1naryth1ef.github.com/disco', icon_url='http://i.imgur.com/1tjdUId.jpg')
embed.title = 'How to create an embed'
embed.url = 'https://b1naryth1ef.github.io/disco/bot_tutorial/message_embeds.html' #This URL will be hooked up to the title of the embed
```
Now, we can add a description and a few fields:
```py
embed.add_field(name='Inline field 1', value='Some value for this field', inline=True)
embed.add_field(name='Inline field 2', value='Another value for another field', inline=True)
embed.add_field(name='Inline field 3', value='Third value for the third field', inline=True)
embed.add_field(name='A non-inline field', value='You can only have a max of 3 inline field on 1 line', inline=False)
embed.description = 'This is the general description of the embed, you can use the Discord supported MD in here too, to make it look extra fancy. For example, creating some **bold** or ~~strikethrough~~ text.'
```
Last up, let's set a footer, color and add a timestamp:
```py
embed.timestamp = datetime.utcnow().isoformat()
embed.set_footer(text='Disco Message Embeds tutorial')
embed.color = '10038562' #This can be any color, but I chose a nice dark red tint
```

Once your embed is finished, you can send it using the `channel.send_message()` message or the `event.msg.reply()` function.
With `channel.send_message()`:
```py
self.state.channels.get(<ChannelID>).send_message('[optional text]', embed=embed)
```
with the `event.msg.reply()` function:
```py
event.msg.reply('[optional text]', embed=embed)
```

The final embed we created in this tutorial would look like this:

![alt text](http://i.imgur.com/G1sUcTm.png "The final embed")

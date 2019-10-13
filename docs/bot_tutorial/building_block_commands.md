# Commands

Commands are a big part of the Discord bot usage. A command can be defined as an order you give to a bot. Basic examples of commands are:
`!help` or `!info`, most bots have either of the two.
In the case of these examples, when you send `!help` or `!info` the bot will reply with a help or info message.

## Basic commands

Creating commands in Disco is really easy because of the [Plugins](https://b1naryth1ef.github.io/disco/bot_tutorial/building_block_plugins.html) that are a core fundamental of Disco. For more info on them, read back in the [Plugins](https://b1naryth1ef.github.io/disco/bot_tutorial/building_block_plugins.html) section of this tutorial. Creating a basic command is done as follows:
First, create a Plugin class:
```py
class myPlugin(Plugin):
```
Now, we can add a command to it. The command will be named ping, and it will simply reply with `pong!`
```py
@Plugin.command('ping')
def on_ping_command(self, event):
  event.msg.reply('Pong!')
```
And there we go! Our very first command!

## Command arguments

Next, lets go on to some more advanced commands. Wye'll create an echo command that will respond with whatever we put in to it.
```py
@Plugin.command('echo', '<content:str...>')
def on_echo_command(self, event, content):
  event.msg.reply(content)
```
What we did here, was add an argument to our command. The argument we created here, content, is required. This means the command won't work if you don't pass in data for the `content` argument.
You can also add optional arguments to a command. Instead of surrounding the name and type in angle brackets, you'd surround them in square brackets like this: `[content:str...]`
Keep in mind that arguments that are optional might not be there. You'll have to create some checks so that your program doesn't crash on unexpected null values.

## Command groups

Now that we have 2 basic commands and we know to create basic commands and add some arguments to it. Let's create a more advanced command utilizing what we just learned.
The command will take 2 numbers (integers) and simply adds them together. It will work like this: `!math add 1 4` and it would return 5. Instead of passing `'math add'` as the command name, we'll be using command groups here.
Using command groups you can easily group commands together and create sub commands. Now, here comes our math command:
```py
@Plugin.command('add', '<a:int> <b:int>', group='math')
def on_add_command(self, event, a, b):
  event.msg.reply('{}'.format(a+b))
```
Here, we added multiple arguments to our command. Namely, number a and number b, that we add together and return back. Of course, you can do loads more fun things with the Disco command handler.

## Optional arguments

Lets create a tag system, that can either store a tag if you'd use it like this: `!tag name value` or retrieve a tag if you'd use it like this: `!tag name`

We'll need 2 arguments. A name argument that's required, and an optional value argument. Inside the command we'll check if a `value` is provided. If there is, we'll store the tag. Otherwise, we'll try to retrieve the previously set value for that tag and return it.
For the sake of this example, we'll assume that the `tags` dict gets stored somewhere so it doesn't get removed after a restart.
```py
tags = {}

@Plugin.command('tag', '<name:str> [value:str...]')
def on_tag_command(self, event, name, value=None):

  if value:
    tags[name] = value
    event.msg.reply(':ok_hand: created tag `{}`'.format(name))
  else:
    if name in tags.keys():
      return event.msg.reply(tags[name])
    else:
      return event.msg.reply('Unknown tag: `{}`'.format(name))
```

## ArgumentParser

A different way of adding arguments to a command is by using `argparse.ArgumentParser`. With `argparser` it's easier to create more complicated commands with many options or flags.
Let's put this into practice by recreating our math add command, but using `argparser`. More info on `argparser` and the `add_argument()` method can be found [here](https://docs.python.org/2/library/argparse.html#the-add-argument-method)
```py
@Plugin.command('add', parser=True, group='math')
@Plugin.parser.add_argument('a', type=int)
@Plugin.parser.add_argument('b', type=int)
def on_add_command(self, event, args):
  event.msg.reply('{}'.format(args.a + args.b)
```

These are all the commands we created in this tutorial:
```py
class myPlugin(Plugin):
  @Plugin.command('ping')
  def on_ping_command(self, event):
    event.msg.reply('Pong!')
    
  @Plugin.command('echo', '<content:str...>')
  def on_echo_command(self, event, content):
    event.msg.reply(content)
    
  @Plugin.command('add', '<a:int> <b:int>', group='math')
  def on_add_command(self, event, a, b):
    event.msg.reply('{}'.format(a+b))

  tags = {}
  @Plugin.command('tag', '<name:str> [value:str...]')
  def on_tag_command(self, event, name, value=None):

    if value:
      tags[name] = value
      event.msg.reply(':ok_hand: created tag `{}`'.format(name))
    else:
      if name in tags.keys():
        return event.msg.reply(tags[name])
      else:
        return event.msg.reply('Unknown tag: `{}`'.format(name))
        
  @Plugin.command('add', parser=True, group='math')
  @Plugin.parser.add_argument('a', type=int)
  @Plugin.parser.add_argument('b', type=int)
  def on_add_command(self, event, args):
    event.msg.reply('{}'.format(args.a + args.b)
```

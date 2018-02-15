# Bot Tutorial

Disco provides a built-in set of tools for building and running Discord bots which can be used to quickly and easily create integrations. Within this tutorial you'll be shown how to install Disco, write plugins, and run bots. This tutorial assumes you've already followed the [Installation Steps](../installation.md).

## Creating a Bot

The first step to creating bots is to actually register them on Discord itself. To do this, you'll need to be logged into your Discord account on the browser and then navigate to [My Apps](https://discordapp.com/developers/applications/me). Here you'll have the option to create a new application, and once created you can add a bot user (by clicking "Create a Bot User") to your application. Finally, you'll want to keep track of the bot user token which can be shown by clicking the "click to reveal" link next to the token field.

Once you have a Discord bot account, you can then setup your workspace. For now we'll just need a folder (perhaps called `disco-tutorial`) with a few files in it:

```
disco-tutorial/
  config.json
  plugins/
    __init__.py
    tutorial.py
```

{% hint style='tip' %}
The \_\_init\_\_.py file is required for Python to find your plugin, but it can remain empty.
{% endhint %}


Now let's setup the configuration file. To start off with we'll paste the following template in and modify our token key (`MY_BOT_TOKEN_HERE`) to be the token we obtained above. The plugins section tells disco what plugins to load, based on a module path (similar to how Python imports work). In this example we're asking disco to load the plugin contained in the tutorial file within the plugins directory (or "module"). Disco by default loads the first plugin it finds within the module, so you want to make sure each plugin class is contained within its own file.

```json
{
  "token": "MY_BOT_TOKEN_HERE",
  "bot": {
    "plugins": [
      "plugins.tutorial"
    ]
  }
}
```


Now we're ready to write our plugin. Plugins are used to isolate the functionality of your bot into components. Plugins can be dynamically loaded, unloaded and reloaded at runtime. Lets start off by writing a plugin with a "ping" command;

```python
from disco.bot import Plugin


class TutorialPlugin(Plugin):
    @Plugin.command('ping')
    def command_ping(self, event):
        event.msg.reply('Pong!')
```

Now that we have a plugin setup and our configuration is ready, we can run and test the bot. We can do this by executing the following command from within our project directory:


```sh
python -m disco.cli --config config.json
```

If all is successful, you can then test your bot by mentioning it with the command, like so:

```
@tutorial#1234 ping
```

At this point, you've achieved the creation and setup of a very simple bot. Now lets work on understanding and working with more Disco features.

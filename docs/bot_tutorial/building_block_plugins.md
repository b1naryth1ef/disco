# Plugins

Plugins are Disco are a core abstraction which attempt to encapsulate the functionality of your bot into contained modules. To boil it down, commands related to one another, or listeners that control the same functionality should be within the same Plugin. Although it's possible to call and pass data between Plugins, you should generally attempt to avoid it.

## Plugin Lifecycle

### Loading

Plugins are loaded when the Bot is initially created, and when this happens the `Plugin.load` function is called. If the plugin is being reloaded, the call to this function will contain a dictionary of data returned by the previous `unload` call. Using this, you can pass data between loaded instances of your plugin to help aid in seamless reloads. Often plugins will require some level of configuration and setup before running, and this code can be inserted within an overridden version of the load function, as such:

```python
class ExamplePlugin(Plugin):
    def load(self, ctx):
        super(ExamplePlugin, self).load(ctx)
        setup_database()
        self.data = ctx.get('data', {})
```

The load function of a plugin is guaranteed to only be called once for the instance, when reloading a new instance of the plugin will be created.

### Unloading

Plugins are unloaded in multiple scenarios (shutdown, before a reload, or during an unload), and when this happens the `Plugin.unload` function is called. This function is passed one argument containing a dictionary, which (if the plugin wants) can be filled with information that a future iteration (in the case we're reloading) of the plugin can use to maintain state. Plugins may want to call or save data before being unloaded, and in this case they can override the unload function:

```python
class ExamplePlugin(Plugin):
    def unload(self, ctx):
        ctx['data'] = self.data
        super(ExamplePlugin, self).unload(ctx)
```

During the unload sequence all greenlets which the plugin owns (e.g. greenlets for command or listener callbacks, any spawned with `Plugin.spawn`) are terminated. In the case where command callbacks should continue execution past the unload point (e.g. in the case where a plugin reloads itself), you should pass `oob=True` to the `Plugin.command` decorator.

## Configuration

Disco supports a framework for dynamically passing configuration to plugins. By default, configuration files live within the `config/` directory, and are named after the plugin, e.g. `ExamplePlugin` would be configured via `config/example.json`. Adding support for configuration within your plugin can be done via a decorator:

```python
from disco.bot import Plugin, PluginConfig

class ExamplePluginConfig(PluginConfig):
    var1 = "test"
    var2 = True


@Plugin.with_config(ExamplePluginConfig)
class ExamplePlugin(Plugin):
    def load(self, ctx):
        super(ExamplePlugin, self).load(ctx)
        assert self.config.var1 == "test"
        assert self.config.var2
```

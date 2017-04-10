# Building a Bot

First up, its important to clarify what a bot describes in Disco-land. Disco has a built-in bot/plugin/command framework, which allows you to quickly and easily build fully functional bots. A bot defines a set of rules for parsing and handling commands, user and role permissions for those commands, and a set of plugins which will be loaded at runtime. 

## Your First Bot

Disco has builtin support for building and running bots, which makes building your first bot extremely easy. 

```
config.yaml
plugin_name/
  plugin_name.py
```

You can replace `plugin_name` with whatever makes the most since for your project
.. currentmodule:: disco

API Reference
=============

Version Information
-------------------
disco exports a top-level variable that can be used to introspect the current
version information for the installed package.

.. data:: VERSION

  A string representation of the current version, in standard semantic
  versioning format. E.g. ``'5.4.3-rc.2'``


Client
------------

.. autoclass:: disco.client.Client
      :members:


State
-----

.. automodule:: disco.state
      :members:


CLI
---

.. automodule:: disco.cli
      :members:


Types
-----

Channel
~~~~~~~

.. automodule:: disco.types.channel
      :members:

Guild
~~~~~

.. automodule:: disco.types.guild
      :members:

Message
~~~~~~~

.. automodule:: disco.types.message
      :members:

User
~~~~

.. automodule:: disco.types.user
      :members:

Voice
~~~~~

.. automodule:: disco.types.voice
      :members:

Invite
~~~~~~

.. automodule:: disco.types.invite
      :members:

Permissions
~~~~~~~~~~~

.. automodule:: disco.types.permissions
      :members:


Bot Toolkit
-----------

.. automodule:: disco.bot.bot
      :members:

Plugins
~~~~~~~

.. automodule:: disco.bot.plugin
      :members:

Commands
~~~~~~~~

.. automodule:: disco.bot.command
      :members:

Command Argument Parser
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: disco.bot.parser
      :members:


Gateway API
-----------

The Gateway API is Discord's real-time websocket based API. Disco includes various functionality for creating and maintaining a persistant/real-time connection over this API.

GatewayClient
~~~~~~~~~~~~~

.. autoclass:: disco.gateway.client.GatewayClient
      :members:

Gateway Events
~~~~~~~~~~~~~~

.. automodule:: disco.gateway.events
      :members:

Sharding
~~~~~~~~

Sharding allows users to improve the performance of their application, and support over 2,500 guilds per account. Disco has native support for sharding, which allows you to transparently communicate between running shards.

.. autoclass:: disco.gateway.sharder.ShardHelper
      :members:

.. autoclass:: disco.gateway.sharder.AutoSharder
      :members:

.. autoclass:: disco.gateway.ipc.GIPCProxy
      :members:


REST API
--------

Disco includes a module which handles all interactions with Discord's HTTP-based REST API. This module has support for various required functions of the API, such as ratelimit headers/backoff, error handling, and type conversions.

APIClient
~~~~~~~~~

.. autoclass:: disco.api.client.APIClient
      :members:
      :undoc-members:

.. autoclass:: disco.api.client.Routes
      :members:
      :undoc-members:

HTTP Utilities
~~~~~~~~~~~~~~
.. autoclass:: disco.api.http.APIException
      :members:

.. autoclass:: disco.api.http.HTTPClient
      :members:

Ratelimit Utilities
~~~~~~~~~~~~~~~~~~~

.. autoclass:: disco.api.ratelimit.RouteState
      :members:

.. autoclass:: disco.api.ratelimit.RateLimiter
      :members:

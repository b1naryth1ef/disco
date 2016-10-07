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

GatewayClient
~~~~~~~~~~~~~

.. autoclass:: disco.gateway.client.GatewayClient
      :members:

Gateway Events
~~~~~~~~~~~~~~

.. automodule:: disco.gateway.client.Events
      :members:


REST API
--------

APIClient
~~~~~~~~~

.. autoclass:: disco.api.client.APIClient
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

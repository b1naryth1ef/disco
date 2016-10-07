.. currentmodule:: disco

Utilities
=========

This section details information about various utilities provided in the disco
package, which aid the development and runtime management of disco clients/bots.
Generally these utilties are situational, and can be enabled depending on
various scenarious developers and users may find themselves in.

Manhole
-------

The manhole utilty is a backdoor server that allows opening a interactive REPL
while the client is running. This can be very useful for attaching and
inspecting runtime state, without distribing the normal client operations. To
enable the backdoor, simply set the
:attr:`disco.client.ClientConfig.manhole_enable` setting, and tweak
:attr:`disco.client.ClientConfig.manhole_bind` settings based on the connection
parameters you'd like.

It's recommended you connect to the manhole via ``rlwrap`` and ``netcat``, which
will give a proper TTY-like readline experience. For example:

.. sourcecode:: bash

    rlwrap netcat localhost 8484

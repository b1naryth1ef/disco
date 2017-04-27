# Installation and Setup

The easiest way to install the base version of Disco is through Python's [pip](https://pip.pypa.io/en/stable/) utility. To simply install the most minimal version of Disco, simply run:

{% hint style='tip' %}
If you are a new Python developer, or are unsure what pip even is, try starting [here](https://packaging.python.org/installing/).
{% endhint %}

```sh
pip install disco-py
```

## Optional Dependencies

Disco also has a set of optional dependencies which add various levels of functionality or support when installed. These can all be installed in a similar fashion to Disco, by simply running:

```sh
pip install DEPENDENCY_NAME
```

| Name | Explanation |
|---------|------------------|
| requests[security] | modern/proper SSL implementation, this helps silence some annoying warning messages |
| ujson | faster json parser, can be used to improve performance |
| erlpack | ETF parser, only supports Python 2.x but will greatly improve Gateway performance and bandwidth usage |
| gipc | IPC library for Gevent which adds support for automatic sharding |
| youtube-dl | adds support for downloading and playing songs from a plethora (including Youtube) of sources |
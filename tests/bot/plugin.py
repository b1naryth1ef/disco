import pytest
from disco.bot.plugin import Plugin, register_plugin_base_class, find_loadable_plugins


def _test_module(**kwargs):
    class MyTestModule(object):
        pass

    m = MyTestModule()

    for k, v in kwargs.items():
        setattr(m, k, v)

    return m


def test_shallow_attribute_deprecated():
    class MyPluginBaseClass(Plugin):
        _shallow = True

    class RegularPlugin(Plugin):
        pass

    with pytest.warns(DeprecationWarning):
        plugins = list(find_loadable_plugins(_test_module(
            MyPluginBaseClass=MyPluginBaseClass,
            RegularPlugin=RegularPlugin,
        )))

    assert plugins == [RegularPlugin]


def test_register_plugin_base_class():
    class MyPluginBaseClass(Plugin):
        pass

    class RegularPlugin(MyPluginBaseClass):
        pass

    register_plugin_base_class(MyPluginBaseClass)

    plugins = list(find_loadable_plugins(_test_module(
        MyPluginBaseClass=MyPluginBaseClass,
        RegularPlugin=RegularPlugin,
    )))

    assert plugins == [RegularPlugin]

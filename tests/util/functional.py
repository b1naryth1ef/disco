from disco.util.functional import simple_cached_property


def test_simple_cached_property():
    class Test(object):
        def __init__(self, a, b):
            self.a = a
            self.b = b

        @simple_cached_property
        def value(self):
            return self.a + self.b

    inst = Test(1, 1)
    assert inst.value == 2

    inst.a = 4
    assert inst.value == 2

    del inst.value
    assert inst.value == 5

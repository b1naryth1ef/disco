from unittest import TestCase
from disco.types.base import Model, Field


class _M(Model):
    a = Field(int)
    b = Field(float)
    c = Field(str)


class TestModel(TestCase):
    def test_model_simple_loading(self):
        inst = _M(dict(a=1, b=1.1, c='test'))
        self.assertEquals(inst.a, 1)
        self.assertEquals(inst.b, 1.1)
        self.assertEquals(inst.c, 'test')

    def test_model_load_into(self):
        inst = _M()
        _M.load_into(inst, dict(a=1, b=1.1, c='test'))
        self.assertEquals(inst.a, 1)
        self.assertEquals(inst.b, 1.1)
        self.assertEquals(inst.c, 'test')

    def test_model_loading_consume(self):
        obj = dict(a=5, b=33.33, c='wtf')
        inst = _M()
        inst.load(obj, consume=True)

        self.assertEquals(obj, {})
        self.assertEquals(inst.a, 5)
        self.assertEquals(inst.b, 33.33)
        self.assertEquals(inst.c, 'wtf')

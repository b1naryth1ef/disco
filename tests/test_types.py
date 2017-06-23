from unittest import TestCase
from disco.types.base import Model, Field


class _A(Model):
    a = Field(int)
    b = Field(float)
    c = Field(str)


class _B(Model):
    a = Field(int)
    b = Field(float)
    c = Field(str)


class _C(Model):
    a = Field(_A)
    b = Field(_B)


class TestModel(TestCase):
    def test_model_simple_loading(self):
        inst = _A(dict(a=1, b=1.1, c='test'))
        self.assertEquals(inst.a, 1)
        self.assertEquals(inst.b, 1.1)
        self.assertEquals(inst.c, 'test')

    def test_model_load_into(self):
        inst = _A()
        _A.load_into(inst, dict(a=1, b=1.1, c='test'))
        self.assertEquals(inst.a, 1)
        self.assertEquals(inst.b, 1.1)
        self.assertEquals(inst.c, 'test')

    def test_model_loading_consume(self):
        obj = {
            'a': {
                'a': 1,
                'b': 2.2,
                'c': '3',
                'd': 'wow',
            },
            'b': {
                'a': 3,
                'b': 2.2,
                'c': '1',
                'z': 'wtf'
            },
            'g': 'lmao'
        }

        inst = _C()
        inst.load(obj, consume=True)

        self.assertEquals(inst.a.a, 1)
        self.assertEquals(inst.b.c, '1')

        self.assertEquals(obj, {'a': {'d': 'wow'}, 'b': {'z': 'wtf'}, 'g': 'lmao'})

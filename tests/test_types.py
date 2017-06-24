from __future__ import print_function

import six

from unittest import TestCase
from holster.enum import Enum
from disco.types.base import Model, Field, enum, snowflake, ConversionError


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
        self.assertEqual(inst.a, 1)
        self.assertEqual(inst.b, 1.1)
        self.assertEqual(inst.c, 'test')

    def test_model_load_into(self):
        inst = _A()
        _A.load_into(inst, dict(a=1, b=1.1, c='test'))
        self.assertEqual(inst.a, 1)
        self.assertEqual(inst.b, 1.1)
        self.assertEqual(inst.c, 'test')

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

        self.assertEqual(inst.a.a, 1)
        self.assertEqual(inst.b.c, '1')

        self.assertEqual(obj, {'a': {'d': 'wow'}, 'b': {'z': 'wtf'}, 'g': 'lmao'})

    def test_model_field_enum(self):
        en = Enum(
            A=1,
            B=2,
            C=3
        )

        class _M(Model):
            field = Field(enum(en))

        self.assertEqual(_M(field=en.A).field, en.A)
        self.assertEqual(_M(field=2).field, en.B)
        self.assertEqual(_M(field='3').field, None)
        self.assertEqual(_M(field='a').field, en.A)
        self.assertEqual(_M(field='A').field, en.A)

    def test_model_field_snowflake(self):
        class _M(Model):
            field = Field(snowflake)

        self.assertEqual(_M(field=327936274851954688).field, 327936274851954688)
        self.assertEqual(_M(field='327936274851954688').field, 327936274851954688)

        with self.assertRaises(ConversionError):
            _M(field='asdf')

    def test_model_field_cast(self):
        class Object(object):
            def __init__(self, v):
                self.v = v

            def __str__(self):
                return self.v

        class _M(Model):
            field = Field(Object, cast=six.text_type)

        inst = _M(field=u'wowza')
        self.assertEqual(inst.to_dict(), {'field': u'wowza'})

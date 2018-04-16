import pytest

from disco.types.base import Model, Field, cached_property, text


@pytest.fixture
def model():
    class TestModel(Model):
        a = Field(int)
        b = Field(int)

        @cached_property
        def value(self):
            return self.a + self.b

    return TestModel


def test_cached_property(model):
    inst = model(a=1, b=3)
    assert inst.value == 4

    inst.a = 2
    assert inst.value == 4


def test_cached_property_clear_on_update(model):
    inst = model(a=1, b=3)
    assert inst.value == 4
    inst.inplace_update(model(a=2, b=3))
    assert inst.value == 5


def test_defaults():
    class TestModel(Model):
        a = Field(int, default=None)
        b = Field(int, default=0)

    model = TestModel()
    assert model.a is None
    assert model.b == 0


def test_text_casting():
    class TestModel(Model):
        a = Field(text)

    model = TestModel({'a': 1})
    assert model.a == '1'

    model = TestModel({'a': {}})
    assert model.a == '{}'

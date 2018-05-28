import pytest
import random

from disco.util.hashmap import HashMap


@pytest.fixture
def hashmap():
    return HashMap({i: random.randint(1, 1000000) for i in range(100000)})


def test_hashmap_insert_performance(benchmark):
    def bench_hashmap_insert(hsh):
        hsh[random.randint(1, 100000)] = True

    benchmark(bench_hashmap_insert, HashMap())


def test_hashmap_lookup_performance(benchmark, hashmap):
    def bench_hashmap_lookup():
        assert hashmap[random.randint(1, 10000)] > 0

    benchmark(bench_hashmap_lookup)


def test_hashmap_find(hashmap):
    assert len(list(hashmap.find(lambda v: v > 0))) == len(hashmap)
    assert hashmap.find_one(lambda v: v > 0) > 0


def test_hashmap_filter(hashmap):
    for item in list(hashmap.filter(lambda v: v % 2 == 0)):
        assert item % 2 == 0


def test_hashmap_builtins(hashmap):
    for item in hashmap:
        assert item in hashmap

    assert hashmap.popitem()[1] > 1


def test_hashmap_items(hashmap):
    assert len(list(hashmap.items())) == 100000
    assert list(hashmap.items())[0][0] == 0
    assert list(hashmap.items())[0][1] == hashmap[0]


def test_hashmap_select_one():
    class Test(object):
        x = 1
        y = 2
    hashmap = HashMap()
    hashmap['x'] = Test()

    assert hashmap.select_one(x=1) == hashmap['x']
    assert hashmap.select_one(x=2) == None

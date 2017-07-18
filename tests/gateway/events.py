from disco.gateway.events import GatewayEvent, Resumed


def create_resumed_payload():
    return GatewayEvent.from_dispatch(None, {
        't': 'RESUMED',
        'd': {
            '_trace': ['test', '1', '2', '3'],
        }
    })


def test_from_dispatch():
    event = create_resumed_payload()
    assert isinstance(event, Resumed)
    assert event.trace == ['test', '1', '2', '3']


def test_event_creation(benchmark):
    benchmark(create_resumed_payload)

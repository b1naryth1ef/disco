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


def test_guild_role_create_guild_id_attach():
    event = GatewayEvent.from_dispatch(None, {
        't': 'GUILD_ROLE_CREATE',
        'd': {
            'role': {
                'id': 1,
                'name': 'test',
                'color': 1,
                'hoist': True,
                'position': 0,
                'permissions': 0,
                'managed': False,
                'mentionable': False,
            },
            'guild_id': 2,
        }
    })

    assert event.guild_id == 2
    assert event.role.guild_id == 2


def test_guild_role_update_guild_id_attach():
    event = GatewayEvent.from_dispatch(None, {
        't': 'GUILD_ROLE_UPDATE',
        'd': {
            'role': {
                'id': 1,
                'name': 'test',
                'color': 1,
                'hoist': True,
                'position': 0,
                'permissions': 0,
                'managed': False,
                'mentionable': False,
            },
            'guild_id': 2,
        }
    })

    assert event.guild_id == 2
    assert event.role.guild_id == 2

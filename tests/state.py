from disco.state import State, StateConfig
from holster.emitter import Emitter
from disco.gateway.events import VoiceStateUpdate


class MockClient(object):
    def __init__(self):
        self.events = Emitter()


def get_state(config=None):
    return State(MockClient(), config or StateConfig())


def test_state_remove_expired_voice_states_device_change():
    state = get_state()

    event = VoiceStateUpdate.create({
        'session_id': 'a',
        'guild_id': 1,
        'channel_id': 1,
        'user_id': 1,
    }, None)
    state.client.events.emit('VoiceStateUpdate', event)

    assert len(state.voice_states) == 1
    assert 'a' in state.voice_states

    event = VoiceStateUpdate.create({
        'session_id': 'b',
        'guild_id': 1,
        'channel_id': 1,
        'user_id': 1,
    }, None)
    state.client.events.emit('VoiceStateUpdate', event)

    assert len(state.voice_states) == 1
    assert 'a' not in state.voice_states
    assert 'b' in state.voice_states

from holster.enum import Enum

from disco.util.oop import TypedClass

OPCode = Enum(
    DISPATCH=0,
    HEARTBEAT=1,
    IDENTIFY=2,
    STATUS_UPDATE=3,
    VOICE_STATE_UPDATE=4,
    VOICE_SERVER_PING=5,
    RESUME=6,
    RECONNECT=7,
    REQUEST_GUILD_MEMBERS=8,
    INVALID_SESSION=9,
    HELLO=10,
    HEARTBEAT_ACK=11,
    GUILD_SYNC=12,
)


class Packet(TypedClass):
    pass


class DispatchPacket(Packet):
    OP = OPCode.DISPATCH

    PARAMS = {
        ('d', 'data'): {},
        ('t', 'event'): str,
    }


class HeartbeatPacket(Packet):
    OP = OPCode.HEARTBEAT

    PARAMS = {
        ('d', 'data'): (int, ),
    }


class IdentifyPacket(Packet):
    OP = OPCode.IDENTIFY

    PARAMS = {
        'token': str,
        'compress': bool,
        'large_threshold': int,
        'shard': [int],
        'properties': 'properties'
    }

    @property
    def properties(self):
        return {
            '$os': 'linux',
            '$browser': 'disco',
            '$device': 'disco',
            '$referrer': '',
        }


class ResumePacket(Packet):
    OP = OPCode.RESUME

    PARAMS = {
        'token': str,
        'session_id': str,
        'seq': int,
    }


class ReconnectPacket(Packet):
    OP = OPCode.RECONNECT


class InvalidSessionPacket(Packet):
    OP = OPCode.INVALID_SESSION


class HelloPacket(Packet):
    OP = OPCode.HELLO

    PARAMS = {
        'heartbeat_interval': int,
        '_trace': [str],
    }


class HeartbeatAckPacket(Packet):
    OP = OPCode.HEARTBEAT_ACK


PACKETS = {
    int(OPCode.DISPATCH): DispatchPacket,
    int(OPCode.HEARTBEAT): HeartbeatPacket,
    int(OPCode.RECONNECT): ReconnectPacket,
    int(OPCode.INVALID_SESSION): InvalidSessionPacket,
    int(OPCode.HELLO): HelloPacket,
    int(OPCode.HEARTBEAT_ACK): HeartbeatAckPacket,
}

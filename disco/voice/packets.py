from holster.enum import Enum

VoiceOPCode = Enum(
    IDENTIFY=0,
    SELECT_PROTOCOL=1,
    READY=2,
    HEARTBEAT=3,
    SESSION_DESCRIPTION=4,
    SPEAKING=5,
)

import struct
import socket
import gevent

from collections import namedtuple

try:
    import nacl.secret
except ImportError:
    print('WARNING: nacl is not installed, voice support is disabled')

from holster.enum import Enum

from disco.util.logging import LoggingClass

AudioCodecs = ('opus',)

RTPPayloadTypes = Enum(OPUS=0x78)

RTCPPayloadTypes = Enum(
    SENDER_REPORT=200,
    RECEIVER_REPORT=201,
    SOURCE_DESCRIPTION=202,
    BYE=203,
    APP=204,
    RTPFB=205,
    PSFB=206,
)

MAX_UINT32 = 4294967295
MAX_SEQUENCE = 65535

RTP_HEADER_VERSION = 0x80  # Only RTP Version is set here (value of 2 << 6)
RTP_EXTENSION_ONE_BYTE = (0xBE, 0xDE)

RTPHeader = namedtuple('RTPHeader', [
    'version',
    'padding',
    'extension',
    'csrc_count',
    'marker',
    'payload_type',
    'sequence',
    'timestamp',
    'ssrc',
])

RTCPHeader = namedtuple('RTCPHeader', [
    'version',
    'padding',
    'reception_count',
    'packet_type',
    'length',
    'ssrc',
])

RTCPData = namedtuple('RTCPData', [
    'client',
    'user_id',
    'payload_type',
    'header',
    'data',
])

VoiceData = namedtuple('VoiceData', [
    'client',
    'user_id',
    'payload_type',
    'rtp',
    'nonce',
    'data',
])


class UDPVoiceClient(LoggingClass):
    def __init__(self, vc):
        super(UDPVoiceClient, self).__init__()
        self.vc = vc

        # The underlying UDP socket
        self.conn = None

        # Connection information
        self.ip = None
        self.port = None
        self.connected = False

        # Voice information
        self.sequence = 0
        self.timestamp = 0

        self._nonce = 0
        self._run_task = None
        self._secret_box = None

        # RTP Header
        self._rtp_audio_header = bytearray(12)
        self._rtp_audio_header[0] = RTP_HEADER_VERSION

    def set_audio_codec(self, codec):
        if codec not in AudioCodecs:
            raise Exception('Unsupported audio codec received, {}'.format(codec))

        ptype = RTPPayloadTypes.get(codec)
        self._rtp_audio_header[1] = ptype.value
        self.log.debug('[%s] Set UDP\'s Audio Codec to %s, RTP payload type %s', self.vc, ptype.name, ptype.value)

    def increment_timestamp(self, by):
        self.timestamp += by
        if self.timestamp > MAX_UINT32:
            self.timestamp = 0

    def setup_encryption(self, encryption_key):
        self._secret_box = nacl.secret.SecretBox(encryption_key)

    def send_frame(self, frame, sequence=None, timestamp=None, incr_timestamp=None):
        # Convert the frame to a bytearray
        frame = bytearray(frame)

        # Pack the rtc header into our buffer
        struct.pack_into('>H', self._rtp_audio_header, 2, sequence or self.sequence)
        struct.pack_into('>I', self._rtp_audio_header, 4, timestamp or self.timestamp)
        struct.pack_into('>i', self._rtp_audio_header, 8, self.vc.ssrc_audio)

        if self.vc.mode == 'xsalsa20_poly1305_lite':
            # Use an incrementing number as a nonce, only first 4 bytes of the nonce is padded on
            self._nonce += 1
            if self._nonce > MAX_UINT32:
                self._nonce = 0

            nonce = bytearray(24)
            struct.pack_into('>I', nonce, 0, self._nonce)
            nonce_padding = nonce[:4]
        elif self.vc.mode == 'xsalsa20_poly1305_suffix':
            # Generate a nonce
            nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
            nonce_padding = nonce
        elif self.vc.mode == 'xsalsa20_poly1305':
            # Nonce is the header
            nonce = bytearray(24)
            nonce[:12] = self._rtp_audio_header
            nonce_padding = None
        else:
            raise Exception('The voice mode, {}, isn\'t supported.'.format(self.vc.mode))

        # Encrypt the payload with the nonce
        payload = self._secret_box.encrypt(bytes(frame), bytes(nonce)).ciphertext

        # Pad the payload with the nonce, if applicable
        if nonce_padding:
            payload += nonce_padding

        # Send the header (sans nonce padding) plus the payload
        self.send(self._rtp_audio_header + payload)

        # Increment our sequence counter
        self.sequence += 1
        if self.sequence >= MAX_SEQUENCE:
            self.sequence = 0

        # Increment our timestamp (if applicable)
        if incr_timestamp:
            self.timestamp += incr_timestamp

    def run(self):
        while True:
            data, addr = self.conn.recvfrom(4096)

            # Data cannot be less than the bare minimum, just ignore
            if len(data) <= 12:
                self.log.debug('[%s] [VoiceData] Received voice data under 13 bytes', self.vc)
                continue

            first, second = struct.unpack_from('>BB', data)

            payload_type = RTCPPayloadTypes.get(second)
            if payload_type:
                length, ssrc = struct.unpack_from('>HI', data, 2)

                rtcp = RTCPHeader(
                    version=first >> 6,
                    padding=(first >> 5) & 1,
                    reception_count=first & 0x1F,
                    packet_type=second,
                    length=length,
                    ssrc=ssrc,
                )

                if rtcp.ssrc == self.vc.ssrc_rtcp:
                    user_id = self.vc.user_id
                else:
                    rtcp_ssrc = rtcp.ssrc
                    if rtcp_ssrc:
                        rtcp_ssrc -= 3
                    user_id = self.vc.audio_ssrcs.get(rtcp_ssrc, None)

                payload = RTCPData(
                    client=self.vc,
                    user_id=user_id,
                    payload_type=payload_type.name,
                    header=rtcp,
                    data=data[8:],
                )

                self.vc.client.gw.events.emit('RTCPData', payload)
            else:
                sequence, timestamp, ssrc = struct.unpack_from('>HII', data, 2)

                rtp = RTPHeader(
                    version=first >> 6,
                    padding=(first >> 5) & 1,
                    extension=(first >> 4) & 1,
                    csrc_count=first & 0x0F,
                    marker=second >> 7,
                    payload_type=second & 0x7F,
                    sequence=sequence,
                    timestamp=timestamp,
                    ssrc=ssrc,
                )

                # Check if rtp version is 2
                if rtp.version != 2:
                    self.log.debug('[%s] [VoiceData] Received an invalid RTP packet version, %s', self.vc, rtp.version)
                    continue

                payload_type = RTPPayloadTypes.get(rtp.payload_type)

                # Unsupported payload type received
                if not payload_type:
                    self.log.debug('[%s] [VoiceData] Received unsupported payload type, %s', self.vc, rtp.payload_type)
                    continue

                nonce = bytearray(24)
                if self.vc.mode == 'xsalsa20_poly1305_lite':
                    nonce[:4] = data[-4:]
                    data = data[:-4]
                elif self.vc.mode == 'xsalsa20_poly1305_suffx':
                    nonce[:24] = data[-24:]
                    data = data[:-24]
                elif self.vc.mode == 'xsalsa20_poly1305':
                    nonce[:12] = data[:12]
                else:
                    self.log.debug('[%s] [VoiceData] Unsupported Encryption Mode, %s', self.vc, self.vc.mode)
                    continue

                try:
                    data = self._secret_box.decrypt(bytes(data[12:]), bytes(nonce))
                except Exception:
                    self.log.debug('[%s] [VoiceData] Failed to decode data from ssrc %s', self.vc, rtp.ssrc)
                    continue

                # RFC3550 Section 5.1 (Padding)
                if rtp.padding:
                    padding_amount, = struct.unpack_from('>B', data[:-1])
                    data = data[-padding_amount:]

                if rtp.extension:
                    # RFC5285 Section 4.2: One-Byte Header
                    rtp_extension_header = struct.unpack_from('>BB', data)
                    if rtp_extension_header == RTP_EXTENSION_ONE_BYTE:
                        data = data[2:]

                        fields_amount, = struct.unpack_from('>H', data)
                        fields = []

                        offset = 4
                        for i in range(fields_amount):
                            first_byte, = struct.unpack_from('>B', data[offset])
                            offset += 1

                            rtp_extension_identifer = first_byte & 0xF
                            rtp_extension_len = ((first_byte >> 4) & 0xF) + 1

                            # Ignore data if identifer == 15, so skip if this is set as 0
                            if rtp_extension_identifer:
                                fields.append(data[offset:offset + rtp_extension_len])

                            offset += rtp_extension_len

                            # skip padding
                            while data[offset] == 0:
                                offset += 1

                        if len(fields):
                            fields.append(data[offset:])
                            data = b''.join(fields)
                        else:
                            data = data[offset:]

                # RFC3550 Section 5.3: Profile-Specific Modifications to the RTP Header
                # clients send it sometimes, definitely on fresh connects to a server, dunno what to do here
                if rtp.marker:
                    self.log.debug('[%s] [VoiceData] Received RTP data with the marker set, skipping', self.vc)
                    continue

                payload = VoiceData(
                    client=self.vc,
                    user_id=self.vc.audio_ssrcs.get(rtp.ssrc, None),
                    payload_type=payload_type.name,
                    rtp=rtp,
                    nonce=nonce,
                    data=data,
                )

                self.vc.client.gw.events.emit('VoiceData', payload)

    def send(self, data):
        self.conn.sendto(data, (self.ip, self.port))

    def disconnect(self):
        self._run_task.kill()

    def connect(self, host, port, timeout=10, addrinfo=None):
        self.ip = socket.gethostbyname(host)
        self.port = port

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if addrinfo:
            ip, port = addrinfo
        else:
            # Send discovery packet
            packet = bytearray(70)
            struct.pack_into('>I', packet, 0, self.vc.ssrc)
            self.send(packet)

            # Wait for a response
            try:
                data, addr = gevent.spawn(lambda: self.conn.recvfrom(70)).get(timeout=timeout)
            except gevent.Timeout:
                return (None, None)

            # Read IP and port
            ip = str(data[4:]).split('\x00', 1)[0]
            port = struct.unpack('<H', data[-2:])[0]

        # Spawn read thread so we don't max buffers
        self.connected = True
        self._run_task = gevent.spawn(self.run)

        return (ip, port)

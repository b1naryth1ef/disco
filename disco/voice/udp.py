import struct
import socket
import gevent

try:
    import nacl.secret
except ImportError:
    print('WARNING: nacl is not installed, voice support is disabled')

from disco.util.logging import LoggingClass

MAX_TIMESTAMP = 4294967295
MAX_SEQUENCE = 65535


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

        self._run_task = None
        self._secret_box = None

        # Buffer used for encoding/sending frames
        self._buffer = bytearray(24)
        self._buffer[0] = 0x80
        self._buffer[1] = 0x78

    def increment_timestamp(self, by):
        self.timestamp += by
        if self.timestamp > MAX_TIMESTAMP:
            self.timestamp = 0

    def setup_encryption(self, encryption_key):
        self._secret_box = nacl.secret.SecretBox(encryption_key)

    def send_frame(self, frame, sequence=None, timestamp=None, incr_timestamp=None):
        # Convert the frame to a bytearray
        frame = bytearray(frame)

        # Pack the rtc header into our buffer
        struct.pack_into('>H', self._buffer, 2, sequence or self.sequence)
        struct.pack_into('>I', self._buffer, 4, timestamp or self.timestamp)
        struct.pack_into('>i', self._buffer, 8, self.vc.ssrc)

        if self.vc.mode == 'xsalsa20_poly1305_suffix':
            nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
            raw = self._secret_box.encrypt(bytes(frame), nonce).ciphertext + nonce
        else:
            # Now encrypt the payload with the nonce as a header
            raw = self._secret_box.encrypt(bytes(frame), bytes(self._buffer)).ciphertext

        # Send the header (sans nonce padding) plus the payload
        self.send(self._buffer[:12] + raw)

        # Increment our sequence counter
        self.sequence += 1
        if self.sequence >= MAX_SEQUENCE:
            self.sequence = 0

        # Increment our timestamp (if applicable)
        if incr_timestamp:
            self.timestamp += incr_timestamp

    def run(self):
        while True:
            self.conn.recvfrom(4096)

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

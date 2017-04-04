import sys
import array
import gevent
import ctypes
import ctypes.util

try:
    from cStringIO import cStringIO as StringIO
except:
    from StringIO import StringIO

from gevent.queue import Queue
from holster.enum import Enum

from disco.util.logging import LoggingClass


c_int_ptr = ctypes.POINTER(ctypes.c_int)
c_int16_ptr = ctypes.POINTER(ctypes.c_int16)
c_float_ptr = ctypes.POINTER(ctypes.c_float)


class EncoderStruct(ctypes.Structure):
    pass


class DecoderStruct(ctypes.Structure):
    pass


EncoderStructPtr = ctypes.POINTER(EncoderStruct)
DecoderStructPtr = ctypes.POINTER(DecoderStruct)


class BaseOpus(LoggingClass):
    BASE_EXPORTED = {
        'opus_strerror': ([ctypes.c_int], ctypes.c_char_p),
    }

    EXPORTED = {}

    def __init__(self, library_path=None):
        self.path = library_path or self.find_library()
        self.lib = ctypes.cdll.LoadLibrary(self.path)

        methods = {}
        methods.update(self.BASE_EXPORTED)
        methods.update(self.EXPORTED)

        for name, item in methods.items():
            func = getattr(self.lib, name)

            if item[0]:
                func.argtypes = item[0]

            func.restype = item[1]

            setattr(self, name, func)

    @staticmethod
    def find_library():
        if sys.platform == 'win32':
            raise Exception('Cannot auto-load opus on Windows, please specify full library path')

        return ctypes.util.find_library('opus')


Application = Enum(
    AUDIO=2049,
    VOIP=2048,
    LOWDELAY=2051
)


Control = Enum(
    SET_BITRATE=4002,
    SET_BANDWIDTH=4008,
    SET_FEC=4012,
    SET_PLP=4014,
)


class OpusEncoder(BaseOpus):
    EXPORTED = {
        'opus_encoder_get_size': ([ctypes.c_int], ctypes.c_int),
        'opus_encoder_create': ([ctypes.c_int, ctypes.c_int, ctypes.c_int, c_int_ptr], EncoderStructPtr),
        'opus_encode': ([EncoderStructPtr, c_int16_ptr, ctypes.c_int, ctypes.c_char_p, ctypes.c_int32], ctypes.c_int32),
        'opus_encoder_ctl': (None, ctypes.c_int32),
        'opus_encoder_destroy': ([EncoderStructPtr], None),
    }

    def __init__(self, sampling, channels, application=Application.AUDIO, library_path=None):
        super(OpusEncoder, self).__init__(library_path)
        self.sampling_rate = sampling
        self.channels = channels
        self.application = application

        self.frame_length = 20
        self.sample_size = 2 * self.channels
        self.samples_per_frame = int(self.sampling_rate / 1000 * self.frame_length)
        self.frame_size = self.samples_per_frame * self.sample_size

        self.inst = self.create()
        self.set_bitrate(128)
        self.set_fec(True)
        self.set_expected_packet_loss_percent(0.15)

    def set_bitrate(self, kbps):
        kbps = min(128, max(16, int(kbps)))
        ret = self.opus_encoder_ctl(self.inst, int(Control.SET_BITRATE), kbps * 1024)

        if ret < 0:
            raise Exception('Failed to set bitrate to {}: {}'.format(kbps, ret))

    def set_fec(self, value):
        ret = self.opus_encoder_ctl(self.inst, int(Control.SET_FEC), int(value))

        if ret < 0:
            raise Exception('Failed to set FEC to {}: {}'.format(value, ret))

    def set_expected_packet_loss_percent(self, perc):
        ret = self.opus_encoder_ctl(self.inst, int(Control.SET_PLP), min(100, max(0, int(perc * 100))))

        if ret < 0:
            raise Exception('Failed to set PLP to {}: {}'.format(perc, ret))

    def create(self):
        ret = ctypes.c_int()
        result = self.opus_encoder_create(self.sampling_rate, self.channels, self.application.value, ctypes.byref(ret))

        if ret.value != 0:
            raise Exception('Failed to create opus encoder: {}'.format(ret.value))

        return result

    def __del__(self):
        if self.inst:
            self.opus_encoder_destroy(self.inst)
            self.inst = None

    def encode(self, pcm, frame_size):
        max_data_bytes = len(pcm)
        pcm = ctypes.cast(pcm, c_int16_ptr)
        data = (ctypes.c_char * max_data_bytes)()

        ret = self.opus_encode(self.inst, pcm, frame_size, data, max_data_bytes)
        if ret < 0:
            raise Exception('Failed to encode: {}'.format(ret))

        # TODO: py3
        return array.array('b', data[:ret]).tostring()


class OpusDecoder(BaseOpus):
    pass


class BufferedOpusEncoder(OpusEncoder):
    def __init__(self, data, *args, **kwargs):
        self.data = StringIO(data)
        self.frames = Queue(kwargs.pop('queue_size', 4096))
        super(BufferedOpusEncoder, self).__init__(*args, **kwargs)
        gevent.spawn(self._encoder_loop)

    def _encoder_loop(self):
        while self.data:
            raw = self.data.read(self.frame_size)
            if len(raw) < self.frame_size:
                break

            self.frames.put(self.encode(raw, self.samples_per_frame))
            gevent.idle()
        self.data = None

    def have_frame(self):
        return self.data or not self.frames.empty()

    def next_frame(self):
        return self.frames.get()


class GIPCBufferedOpusEncoder(OpusEncoder):
    FIN = 1

    def __init__(self, data, *args, **kwargs):
        import gipc

        self.data = StringIO(data)
        self.parent_pipe, self.child_pipe = gipc.pipe(duplex=True)
        self.frames = Queue(kwargs.pop('queue_size', 4096))
        super(GIPCBufferedOpusEncoder, self).__init__(*args, **kwargs)

        gipc.start_process(target=self._encoder_loop, args=(self.child_pipe, (args, kwargs)))

        gevent.spawn(self._writer)
        gevent.spawn(self._reader)

    def _reader(self):
        while True:
            data = self.parent_pipe.get()
            if data == self.FIN:
                return

            self.frames.put(data)
        self.parent_pipe = None

    def _writer(self):
        while self.data:
            raw = self.data.read(self.frame_size)
            if len(raw) < self.frame_size:
                break

            self.parent_pipe.put(raw)
            gevent.idle()

        self.parent_pipe.put(self.FIN)

    def have_frame(self):
        return self.parent_pipe

    def next_frame(self):
        return self.frames.get()

    @classmethod
    def _encoder_loop(cls, pipe, (args, kwargs)):
        encoder = OpusEncoder(*args, **kwargs)

        while True:
            data = pipe.get()
            if data == cls.FIN:
                pipe.put(cls.FIN)
                return

            pipe.put(encoder.encode(data, encoder.samples_per_frame))

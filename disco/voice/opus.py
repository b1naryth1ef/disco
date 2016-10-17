import sys
import array
import ctypes
import ctypes.util

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

            if item[1]:
                func.argtypes = item[1]

            func.restype = item[2]

            setattr(self, name.replace('opus_', ''), func)

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
        super(OpusDecoder, self).__init__(library_path)
        self.sampling_rate = sampling
        self.channels = channels
        self.application = application

        self.frame_length = 20
        self.sample_size = 2 * self.channels
        self.samples_per_frame = int(self.sampling_rate / 1000 * self.frame_length)
        self.frame_size = self.samples_per_frame * self.sample_size

        self.inst = self.create()

    def create(self):
        ret = ctypes.c_int()
        result = self.encoder_create(self.sampling_rate, self.channels, self.application.value, ctypes.byref(ret))

        if ret.value != 0:
            raise Exception('Failed to create opus encoder: {}'.format(ret.value))

        return result

    def __del__(self):
        if self.inst:
            self.encoder_destroy(self.inst)
            self.inst = None

    def encode(self, pcm, frame_size):
        max_data_bytes = len(pcm)
        pcm = ctypes.cast(pcm, c_int16_ptr)
        data = (ctypes.c_char * max_data_bytes)()

        ret = self.encode(self.inst, pcm, frame_size, data, max_data_bytes)
        if ret < 0:
            raise Exception('Failed to encode: {}'.format(ret))

        return array.array('b', data[:ret]).tobytes()


class OpusDecoder(BaseOpus):
    pass

import six
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

    def __init__(self, sampling_rate, channels, application=Application.AUDIO, library_path=None):
        super(OpusEncoder, self).__init__(library_path)
        self.sampling_rate = sampling_rate
        self.channels = channels
        self.application = application

        self._inst = None

    @property
    def inst(self):
        if not self._inst:
            self._inst = self.create()
            self.set_bitrate(128)
            self.set_fec(True)
            self.set_expected_packet_loss_percent(0.15)
        return self._inst

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
        if hasattr(self, '_inst') and self._inst:
            self.opus_encoder_destroy(self._inst)
            self._inst = None

    def encode(self, pcm, frame_size):
        max_data_bytes = len(pcm)
        pcm = ctypes.cast(pcm, c_int16_ptr)
        data = (ctypes.c_char * max_data_bytes)()

        ret = self.opus_encode(self.inst, pcm, frame_size, data, max_data_bytes)
        if ret < 0:
            raise Exception('Failed to encode: {}'.format(ret))

        # TODO: py3
        if six.PY3:
            return array.array('b', data[:ret]).tobytes()
        else:
            return array.array('b', data[:ret]).tostring()


class OpusDecoder(BaseOpus):
    pass

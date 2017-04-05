import gevent
import struct
import subprocess


from gevent.queue import Queue

from disco.voice.opus import OpusEncoder


try:
    from cStringIO import cStringIO as StringIO
except:
    from StringIO import StringIO


OPUS_HEADER_SIZE = struct.calcsize('<h')


class BasePlayable(object):
    pass



class FFmpegPlayable(BasePlayable):
    def __init__(self, source='-', command='avconv', sampling_rate=48000, channels=2, **kwargs):
        self.source = source
        self.command = command
        self.sampling_rate = sampling_rate
        self.channels = channels
        self.kwargs = kwargs

        self._buffer = None
        self._proc = None
        self._child = None

    @classmethod
    def create(_cls, *args, **kwargs):
        cls = kwargs.pop('cls', BufferedOpusEncoder)
        playable = _cls(*args, **kwargs)
        playable.pipe(cls)
        return playable

    @classmethod
    def create_youtube_dl(_cls, url, *args, **kwargs):
        import youtube_dl

        ydl = youtube_dl.YoutubeDL({'format': 'webm[abr>0]/bestaudio/best'})
        info = ydl.extract_info(url, download=False)
        entries = [info] if 'entries' not in info else info['entries']

        for entry in entries:
            playable = _cls.create(entry['url'], *args, **kwargs)
            playable.info = entry
            yield playable

    @property
    def stdout(self):
        return self.proc.stdout

    def read(self, sz):
        if self.streaming:
            return self.proc.stdout.read(sz)
        else:
            if not self._buffer:
                data, _ = self.proc.communicate()
                self._buffer = StringIO(data)
            return self._buffer.read(sz)

    def pipe(self, other, streaming=True):
        if issubclass(other, OpusEncoder):
            self._child = other(self, self.sampling_rate, self.channels, **self.kwargs)
        else:
            raise TypeError('Invalid pipe target')

    @property
    def samples_per_frame(self):
        return self._child.samples_per_frame

    @property
    def proc(self):
        if not self._proc:
            args = [
                self.command,
                '-i', self.source,
                '-f', 's16le',
                '-ar', str(self.sampling_rate),
                '-ac', str(self.channels),
                '-loglevel', 'warning',
                'pipe:1'
            ]
            self._proc = subprocess.Popen(args, stdin=None, stdout=subprocess.PIPE)
        return self._proc

    def have_frame(self):
        return self._child and self._child.have_frame()

    def next_frame(self):
        return self._child.next_frame()


class OpusFilePlayable(BasePlayable):
    """
    A Playable which supports reading from an on-disk opus-format file. This is
    useful in combination with other playables and the OpusFileOutputDuplex.
    """

    def __init__(self, obj, sampling_rate=48000, frame_length=20, channels=2):
        super(OpusFilePlayable, self).__init__()
        self.obj = obj
        self.sampling_rate = sampling_rate
        self.frame_length = frame_length
        self.channels = channels
        self.samples_per_frame = int(self.sampling_rate / 1000 * self.frame_length)

    def have_frame(self):
        return self.obj

    def next_frame(self):
        header = self.obj.read(OPUS_HEADER_SIZE)
        if len(header) < OPUS_HEADER_SIZE:
            self.obj = None
            return

        size = struct.unpack('<h', header)[0]
        raw = self.obj.read(size)
        if len(raw) < size:
            self.obj = None
            return

        return raw


class BufferedOpusEncoder(BasePlayable, OpusEncoder):
    def __init__(self, source, *args, **kwargs):
        self.source = source
        self.frames = Queue(kwargs.pop('queue_size', 4096))
        super(BufferedOpusEncoder, self).__init__(*args, **kwargs)
        gevent.spawn(self._encoder_loop)

    def _encoder_loop(self):
        while self.source:
            raw = self.source.read(self.frame_size)
            if len(raw) < self.frame_size:
                break

            self.frames.put(self.encode(raw, self.samples_per_frame))
            gevent.idle()
        self.source = None

    def have_frame(self):
        return self.source or not self.frames.empty()

    def next_frame(self):
        return self.frames.get()


class GIPCBufferedOpusEncoder(BasePlayable, OpusEncoder):
    FIN = 1

    def __init__(self, source, *args, **kwargs):
        import gipc

        self.source = source
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
            raw = self.source.read(self.frame_size)
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


class DCADOpusEncoder(BasePlayable, OpusEncoder):
    def __init__(self, source, *args, **kwargs):
        self.source = source
        self.command = kwargs.pop('command', 'dcad')
        super(DCADOpusEncoder, self).__init__(*args, **kwargs)
        self._proc = None

    @property
    def proc(self):
        if not self._proc:
            self._proc = subprocess.Popen([
                self.command,
                '--channels', str(self.channels),
                '--rate', str(self.sampling_rate),
                '--size', str(self.samples_per_frame),
                '--bitrate', '128',
                '--fec',
                '--packet-loss-percent', '30',
                '--input', 'pipe:0',
                '--output', 'pipe:1',
            ], stdin=self.source.stdout, stdout=subprocess.PIPE)
        return self._proc

    def have_frame(self):
        return bool(self.proc)

    def next_frame(self):
        header = self.proc.stdout.read(OPUS_HEADER_SIZE)
        if len(header) < OPUS_HEADER_SIZE:
            self._proc = None
            return

        size = struct.unpack('<h', header)[0]

        data = self.proc.stdout.read(size)
        if len(data) == 0:
            self._proc = None
            return

        return data


class OpusDuplexEncoder(BasePlayable):
    def __init__(self, out, encoder, flush=False):
        self.out = out
        self.flush = flush
        self.encoder = encoder
        self.closed = False

    def __getattr__(self, attr):
        return getattr(self.encoder, attr)

    def close(self):
        if self.closed:
            return

        self.closed = True
        self.out.flush()
        self.out.close()

    def have_frame(self):
        have = self.encoder.have_frame()
        if not have:
            self.close()
        return have

    def next_frame(self):
        frame = self.encoder.next_frame()

        if frame:
            self.out.write(struct.pack('<h', len(frame)))
            self.out.write(frame)

            if self.flush:
                self.out.flush()
        else:
            self.close()
        return frame

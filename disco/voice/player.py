import time
import gevent
import struct
import subprocess

from six.moves import queue
from holster.enum import Enum
from holster.emitter import Emitter

from disco.voice.client import VoiceState
from disco.voice.opus import OpusEncoder, BufferedOpusEncoder

try:
    from cStringIO import cStringIO as StringIO
except:
    from StringIO import StringIO


class FFmpegPlayable(object):
    def __init__(self, source='-', command='avconv', sampling_rate=48000, channels=2, **kwargs):
        self.source = source
        self.command = command
        self.sampling_rate = sampling_rate
        self.channels = channels
        self.kwargs = kwargs

        self._buffer = None
        self._proc = None
        self._child = None

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


def create_ffmpeg_playable(*args, **kwargs):
    cls = kwargs.pop('cls', BufferedOpusEncoder)
    playable = FFmpegPlayable(*args, **kwargs)
    playable.pipe(cls)
    return playable


def create_youtube_dl_playables(url, *args, **kwargs):
    import youtube_dl

    ydl = youtube_dl.YoutubeDL({'format': 'webm[abr>0]/bestaudio/best'})
    info = ydl.extract_info(url, download=False)
    entries = [info] if 'entries' not in info else info['entries']

    for entry in entries:
        playable = create_ffmpeg_playable(entry['url'], *args, **kwargs)
        playable.info = entry
        yield playable


class OpusPlayable(object):
    """
    Represents a Playable item which is a cached set of Opus-encoded bytes.
    """
    def __init__(self, sampling_rate=48000, frame_length=20, channels=2):
        self.frames = []
        self.idx = 0
        self.frame_length = 20
        self.sampling_rate = sampling_rate
        self.frame_length = frame_length
        self.channels = channels
        self.sample_size = int(self.sampling_rate / 1000 * self.frame_length)

    @classmethod
    def from_raw_file(cls, path):
        inst = cls()
        obj = open(path, 'r')

        while True:
            buff = obj.read(2)
            if not buff:
                return inst
            size = struct.unpack('<h', buff)[0]
            inst.frames.append(obj.read(size))

    def have_frame(self):
        return self.idx + 1 < len(self.frames)

    def next_frame(self):
        self.idx += 1
        return self.frames[self.idx]


class Player(object):
    Events = Enum(
        'START_PLAY',
        'STOP_PLAY',
        'PAUSE_PLAY',
        'RESUME_PLAY',
        'DISCONNECT'
    )

    def __init__(self, client):
        self.client = client

        # Queue contains playable items
        self.queue = queue.Queue()

        # Whether we're playing music (true for lifetime)
        self.playing = True

        # Set to an event when playback is paused
        self.paused = None

        # Current playing item
        self.now_playing = None

        # Current play task
        self.play_task = None

        # Core task
        self.run_task = gevent.spawn(self.run)

        # Event triggered when playback is complete
        self.complete = gevent.event.Event()

        # Event emitter for metadata
        self.events = Emitter(gevent.spawn)

    def disconnect(self):
        self.client.disconnect()
        self.events.emit(self.Events.DISCONNECT)

    def skip(self):
        self.play_task.kill()

    def pause(self):
        if self.paused:
            return
        self.paused = gevent.event.Event()
        self.events.emit(self.Events.PAUSE_PLAY)

    def resume(self):
        self.paused.set()
        self.paused = None
        self.events.emit(self.Events.RESUME_PLAY)

    def play(self, item):
        start = time.time()
        loops = 0

        while True:
            loops += 1

            if self.paused:
                self.client.set_speaking(False)
                self.paused.wait()
                gevent.sleep(2)
                self.client.set_speaking(True)

            if self.client.state == VoiceState.DISCONNECTED:
                return

            if self.client.state != VoiceState.CONNECTED:
                self.client.state_emitter.wait(VoiceState.CONNECTED)

            if not item.have_frame():
                return

            frame = item.next_frame()
            if frame is None:
                return

            self.client.send_frame(frame)
            self.client.timestamp += item.samples_per_frame

            next_time = start + 0.02 * loops
            delay = max(0, 0.02 + (next_time - time.time()))
            gevent.sleep(delay)

    def run(self):
        self.client.set_speaking(True)

        while self.playing:
            self.now_playing = self.queue.get()

            self.events.emit(self.Events.START_PLAY, self.now_playing)
            self.play_task = gevent.spawn(self.play, self.now_playing)
            self.play_task.join()
            self.events.emit(self.Events.STOP_PLAY, self.now_playing)

            if self.client.state == VoiceState.DISCONNECTED:
                self.playing = False
                self.complete.set()
                return

        self.client.set_speaking(False)
        self.disconnect()

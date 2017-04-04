import time
import gevent
import struct
import subprocess

from six.moves import queue

from disco.voice.client import VoiceState
from disco.voice.opus import BufferedOpusEncoder, GIPCBufferedOpusEncoder


class BaseFFmpegPlayable(object):
    def __init__(self, source='-', command='avconv', sampling_rate=48000, channels=2, **kwargs):
        args = [command, '-i', source, '-f', 's16le', '-ar', str(sampling_rate), '-ac', str(channels), '-loglevel', 'warning', 'pipe:1']
        self.proc = subprocess.Popen(args, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data, _ = self.proc.communicate()
        super(BaseFFmpegPlayable, self).__init__(data, sampling_rate, channels, **kwargs)


class FFmpegPlayable(BaseFFmpegPlayable, BufferedOpusEncoder):
    pass


class GIPCFFmpegPlayable(BaseFFmpegPlayable, GIPCBufferedOpusEncoder):
    pass


def create_youtube_dl_playable(url, cls=FFmpegPlayable, *args, **kwargs):
    import youtube_dl

    ydl = youtube_dl.YoutubeDL({'format': 'webm[abr>0]/bestaudio/best'})
    info = ydl.extract_info(url, download=False)

    if 'entries' in info:
        info = info['entries'][0]

    return cls(info['url'], *args, **kwargs), info


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
    def __init__(self, client):
        self.client = client
        self.queue = queue.Queue()
        self.playing = True
        self.run_task = gevent.spawn(self.run)
        self.paused = None
        self.complete = gevent.event.Event()

    def disconnect(self):
        self.client.disconnect()

    def pause(self):
        if self.paused:
            return
        self.paused = gevent.event.Event()

    def resume(self):
        self.paused.set()
        self.paused = None

    def play(self, item):
        start = time.time()
        loops = 0
        timestamp = 0

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

            self.client.send_frame(item.next_frame(), loops, timestamp)
            timestamp += item.samples_per_frame
            next_time = start + 0.02 * loops
            delay = max(0, 0.02 + (next_time - time.time()))
            gevent.sleep(delay)

    def run(self):
        self.client.set_speaking(True)

        while self.playing:
            self.play(self.queue.get())

            if self.client.state == VoiceState.DISCONNECTED:
                self.playing = False
                self.complete.set()
                return

        self.client.set_speaking(False)
        self.disconnect()

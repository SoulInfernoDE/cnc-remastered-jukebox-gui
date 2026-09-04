# -*- coding: utf-8 -*-
"""Playback for the tracks inside MUSIC.MEG.

The archive holds Microsoft ADPCM WAVs.  Each track is decoded to plain PCM
with ffmpeg - already required by this project - and pushed to a system audio
sink.  Qt Multimedia is deliberately not used: its ALSA/PulseAudio plugins
live in a separate package (libqt5multimedia5-plugins, qt5-qtmultimedia) that
is often absent, and QAudioOutput then silently falls back to a null device.
Writing to paplay/aplay/ffplay instead works wherever the desktop has sound.

Nothing is written to disk; the decoded audio stays in memory.
"""

import shutil
import subprocess
import threading
import time

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

RATE = 44100
CHANNELS = 2
SAMPLE_BYTES = 2
FRAME = CHANNELS * SAMPLE_BYTES
BYTES_PER_SECOND = RATE * FRAME
CHUNK = BYTES_PER_SECOND // 20            # 50 ms, so volume changes apply fast

# Volume is applied to the samples themselves, which keeps changes smooth and
# avoids restarting the sink.  numpy if present, else the stdlib's audioop
# (gone in Python 3.13), else the audio plays unattenuated.
try:
    import numpy as _np
except ImportError:
    _np = None
try:
    import audioop as _audioop
except ImportError:
    _audioop = None


def _gain(data, factor):
    if factor >= 0.999:
        return data
    if _np is not None:
        a = _np.frombuffer(data, dtype="<i2").astype(_np.float32) * factor
        return _np.clip(a, -32768, 32767).astype("<i2").tobytes()
    if _audioop is not None:
        return _audioop.mul(data, SAMPLE_BYTES, factor)
    return data


def _sink_command():
    """The first available raw-PCM sink, most desktop-native first."""
    if shutil.which("paplay"):
        return ["paplay", "--raw", "--format=s16le",
                "--rate=%d" % RATE, "--channels=%d" % CHANNELS]
    if shutil.which("aplay"):
        return ["aplay", "-q", "-f", "S16_LE",
                "-r", str(RATE), "-c", str(CHANNELS), "-"]
    if shutil.which("ffplay"):
        return ["ffplay", "-hide_banner", "-loglevel", "error", "-nodisp",
                "-autoexit", "-f", "s16le", "-ar", str(RATE),
                "-ac", str(CHANNELS), "-i", "pipe:0"]
    return None


def decode(wav_bytes):
    """ADPCM WAV -> signed 16-bit little-endian stereo PCM at 44.1 kHz."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
         "-f", "s16le", "-acodec", "pcm_s16le", "-ac", str(CHANNELS),
         "-ar", str(RATE), "pipe:1"],
        input=wav_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace").strip()[:200])
    return p.stdout


class Player(QObject):
    """One track at a time, decoded off the GUI thread."""

    positionChanged = pyqtSignal(float)     # seconds
    stateChanged = pyqtSignal(str)          # playing | paused | stopped
    trackFinished = pyqtSignal()
    failed = pyqtSignal(str)

    # Emitted from worker threads; Qt queues them onto the GUI thread, which
    # is the only safe way to hand results back.
    _decoded = pyqtSignal(int, object, bool)
    _error = pyqtSignal(int, str)
    _ended = pyqtSignal(int)

    def __init__(self, parent=None):
        super(Player, self).__init__(parent)
        self._pcm = b""
        self._volume = 0.8
        self._state = "stopped"
        self._token = 0             # invalidates work for superseded tracks
        self._run = 0               # invalidates a running sink
        self._proc = None
        self._offset = 0.0          # where the current sink started, seconds
        self._t0 = 0.0

        self._decoded.connect(self._on_decoded)
        self._error.connect(self._on_error)
        self._ended.connect(self._on_ended)

        self._tick = QTimer(self)
        self._tick.setInterval(100)
        self._tick.timeout.connect(lambda: self.positionChanged.emit(self.position))

    # -- state -----------------------------------------------------------
    @property
    def state(self):
        return self._state

    @property
    def duration(self):
        return len(self._pcm) / float(BYTES_PER_SECOND)

    @property
    def position(self):
        if self._state != "playing":
            return self._offset
        return min(self._offset + (time.monotonic() - self._t0), self.duration)

    def _set_state(self, s):
        if s != self._state:
            self._state = s
            self.stateChanged.emit(s)

    # -- loading ---------------------------------------------------------
    def load(self, wav_bytes, autoplay=True):
        self.stop()
        self._token += 1
        token = self._token

        def work():
            try:
                pcm = decode(wav_bytes)
            except Exception as e:
                self._error.emit(token, str(e))
                return
            self._decoded.emit(token, pcm, autoplay)

        threading.Thread(target=work, daemon=True).start()

    def _on_decoded(self, token, pcm, autoplay):
        if token != self._token:
            return                                   # a newer track won
        self._pcm = pcm
        self._offset = 0.0
        if autoplay:
            self._start(0.0)
        else:
            self._set_state("paused")
        self.positionChanged.emit(0.0)

    def _on_error(self, token, msg):
        if token == self._token:
            self.failed.emit(msg)

    # -- transport -------------------------------------------------------
    def _start(self, seconds):
        cmd = _sink_command()
        if cmd is None:
            self.failed.emit("No audio sink found (paplay, aplay or ffplay).")
            return
        self._kill()
        self._run += 1
        run = self._run
        start = max(0, min(len(self._pcm) - FRAME,
                           int(seconds * BYTES_PER_SECOND)))
        start -= start % FRAME
        self._offset = start / float(BYTES_PER_SECOND)
        self._t0 = time.monotonic()

        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except OSError as e:
            self.failed.emit(str(e))
            return
        self._proc = proc
        data = self._pcm

        def pump():
            pos = start
            try:
                while pos < len(data) and run == self._run:
                    end = min(pos + CHUNK, len(data))
                    proc.stdin.write(_gain(data[pos:end], self._volume))
                    pos = end
                proc.stdin.close()
            except (BrokenPipeError, ValueError, OSError):
                return
            proc.wait()
            if run == self._run:
                self._ended.emit(run)

        threading.Thread(target=pump, daemon=True).start()
        self._tick.start()
        self._set_state("playing")

    def _kill(self):
        self._run += 1                                # orphan the pump thread
        self._tick.stop()
        if self._proc is not None:
            try:
                self._proc.kill()
            except OSError:
                pass
            self._proc = None

    def _on_ended(self, run):
        if run != self._run:
            return
        self._tick.stop()
        self._offset = self.duration
        self._set_state("stopped")
        self.trackFinished.emit()

    def play(self):
        if self._pcm and self._state != "playing":
            self._start(self._offset if self._offset < self.duration else 0.0)

    def pause(self):
        if self._state == "playing":
            at = self.position
            self._kill()
            self._offset = at
            self._set_state("paused")

    def toggle(self):
        self.pause() if self._state == "playing" else self.play()

    def stop(self):
        self._kill()
        self._pcm = b""
        self._offset = 0.0
        self._set_state("stopped")

    def seek(self, seconds):
        if not self._pcm:
            return
        if self._state == "playing":
            self._start(seconds)
        else:
            self._offset = max(0.0, min(seconds, self.duration))
        self.positionChanged.emit(self.position)

    def set_volume(self, v):
        self._volume = max(0.0, min(1.0, v))          # picked up by the pump

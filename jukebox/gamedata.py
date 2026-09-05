# -*- coding: utf-8 -*-
"""Reads the jukebox's data straight out of an installed copy of the game.

Nothing here is redistributed: every byte comes from the player's own
installation at runtime.  See docs/FILE-FORMATS.md for the container formats.
"""

import locale
import os
import re
import struct
import threading

MEG_MAGIC = 0x3F7D70A4

XML_PATH = "DATA\\XML\\AUDIO\\AUDIO_SYSTEM_CONSTANTS.XML"
# SFX3D.MEG and SFX2D_ALL.MEG store bare names; SFX2D_<LANG>.MEG nests them
# under the language and repeats it in the filename.
LOC_PATH = "DATA\\TEXT\\MASTERTEXTFILE_{}.LOC"

# The nine languages the game ships, and how a POSIX locale maps onto them.
LANGUAGES = ("EN-US", "DE-DE", "ES-ES", "FR-FR", "KO-KR",
             "PL-PL", "RU-RU", "ZH-CN", "ZH-TW")
_LANG_MAP = {"de": "DE-DE", "es": "ES-ES", "fr": "FR-FR", "ko": "KO-KR",
             "pl": "PL-PL", "ru": "RU-RU", "en": "EN-US"}


class GameDataError(Exception):
    pass


def system_language(available):
    """Picks the game language matching the system locale, else EN-US."""
    tag = ""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        if os.environ.get(var):
            tag = os.environ[var]
            break
    if not tag:
        try:
            tag = locale.getdefaultlocale()[0] or ""
        except (ValueError, TypeError):
            tag = ""
    tag = tag.split(":")[0].split(".")[0].replace("_", "-")
    if not tag:
        return "EN-US"

    lo = tag.lower()
    for cand in available:                      # exact match, e.g. de-DE
        if cand.lower() == lo:
            return cand
    if lo.startswith("zh"):                     # zh-TW / zh-HK are traditional
        want = "ZH-TW" if re.search(r"tw|hk|hant", lo) else "ZH-CN"
        if want in available:
            return want
    want = _LANG_MAP.get(lo.split("-")[0])
    if want in available:
        return want
    return "EN-US" if "EN-US" in available else (available[0] if available else "EN-US")


def find_game_dir():
    env = os.environ.get("CNC_REMASTERED_DIR")
    if env:
        return env
    home = os.path.expanduser("~")
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    roots = [os.path.join(home, ".steam", "steam"),
             os.path.join(home, ".steam", "root"),
             os.path.join(home, ".steam", "debian-installation"),
             os.path.join(xdg, "Steam"),
             os.path.join(home, ".local", "share", "Steam"),
             os.path.join(home, ".var", "app", "com.valvesoftware.Steam",
                          ".local", "share", "Steam"),
             os.path.join(home, "snap", "steam", "common", ".local", "share", "Steam")]
    for r in list(roots):
        for vdf in (os.path.join(r, "steamapps", "libraryfolders.vdf"),
                    os.path.join(r, "config", "libraryfolders.vdf")):
            try:
                with open(vdf, encoding="utf-8", errors="replace") as f:
                    roots += re.findall(r'"path"\s+"([^"]+)"', f.read())
            except OSError:
                pass
    seen = set()
    for r in roots:
        cand = os.path.join(r, "steamapps", "common", "CnCRemastered")
        if cand not in seen:
            seen.add(cand)
            if os.path.isfile(os.path.join(cand, "Data", "MUSIC.MEG")):
                return cand
    return None


class Meg(object):
    """Petroglyph MEG V3 archive."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            first, second = struct.unpack("<II", f.read(8))
            if first == 0xFFFFFFFF and second == MEG_MAGIC:
                base = 8
            elif first == MEG_MAGIC:
                base = 4
            else:
                raise GameDataError("%s is not a MEG V3 archive" % path)
            f.seek(base)
            data_start, n_names, n_files, tbl_size = struct.unpack("<4I", f.read(16))
            tbl, names, o = f.read(tbl_size), [], 0
            while o < len(tbl):
                ln = struct.unpack_from("<H", tbl, o)[0]
                o += 2
                names.append(tbl[o:o + ln].decode("ascii", "replace"))
                o += ln
            if data_start - (base + 16 + tbl_size) < n_files * 20:
                raise GameDataError("%s: file table too short" % path)
            recs = f.read(n_files * 20)

        self.entries = []
        self._index = {}
        for i in range(n_files):
            size, offset = struct.unpack_from("<II", recs, i * 20 + 10)
            ni = struct.unpack_from("<H", recs, i * 20 + 18)[0]
            name = names[ni]
            self.entries.append((name, size, offset))
            self._index[name.lower()] = (size, offset)
        self._local = threading.local()

    def _fh(self):
        fh = getattr(self._local, "fh", None)
        if fh is None:
            fh = self._local.fh = open(self.path, "rb")
        return fh

    def read(self, offset, size):
        fh = self._fh()
        fh.seek(offset)
        return fh.read(size)

    def get(self, name):
        hit = self._index.get(name.lower())
        return self.read(hit[1], hit[0]) if hit else None

    def find(self, pattern):
        """Yields (basename_without_extension, bytes) for a regex on the path."""
        rx = re.compile(pattern, re.I)
        for name, size, offset in self.entries:
            if rx.search(name):
                stem = os.path.splitext(name.split("\\")[-1])[0]
                yield stem, self.read(offset, size)


def parse_loc(data):
    """MASTERTEXTFILE_<LANG>.LOC -> {key: text}."""
    n = struct.unpack_from("<I", data, 0)[0]
    recs = [struct.unpack_from("<III", data, 4 + i * 12) for i in range(n)]
    o = 4 + n * 12
    values = []
    for _, vlen, _ in recs:
        values.append(data[o:o + vlen * 2].decode("utf-16-le", "replace"))
        o += vlen * 2
    keys = []
    for _, _, klen in recs:
        keys.append(data[o:o + klen].decode("ascii", "replace"))
        o += klen
    if o != len(data):
        raise GameDataError("MASTERTEXTFILE: read %d of %d bytes" % (o, len(data)))
    return dict(zip(keys, values))


class Track(object):
    __slots__ = ("title", "game", "type", "seconds", "bonus_locked",
                 "filename", "size", "offset")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    @property
    def is_ra(self):
        return self.game == "Red_Alert"

    @property
    def duration_text(self):
        s = int(self.seconds or 0)
        return "%02d:%02d" % (s // 60, s % 60)


class GameData(object):
    """Everything the jukebox needs: localised strings and the track list."""

    def __init__(self, game_dir=None, language=None):
        self.game_dir = game_dir or find_game_dir()
        if not self.game_dir:
            raise GameDataError(
                "Command & Conquer Remastered Collection not found.\n"
                "Pass --game or set CNC_REMASTERED_DIR.")
        data = os.path.join(self.game_dir, "Data")
        for name in ("MUSIC.MEG", "CONFIG.MEG", "TEXTURES_SRGB.MEG"):
            if not os.path.isfile(os.path.join(data, name)):
                raise GameDataError("Not found: %s" % os.path.join(data, name))

        self.config = Meg(os.path.join(data, "CONFIG.MEG"))
        self.music = Meg(os.path.join(data, "MUSIC.MEG"))
        self.textures = Meg(os.path.join(data, "TEXTURES_SRGB.MEG"))
        self._data_dir = data
        self._sfx_megs = {}                 # language -> archives, opened once

        have = [l for l in LANGUAGES
                if self.config.get(LOC_PATH.format(l)) is not None]
        self.language = language if language in have else system_language(have)
        self.available_languages = have

        raw = self.config.get(LOC_PATH.format(self.language))
        if raw is None:
            raise GameDataError("No string table for %s" % self.language)
        self._text = parse_loc(raw)

        self.tracks = self._build_tracks()

    # -- strings ---------------------------------------------------------
    def text(self, key, default=""):
        # "&&" is the UI framework's escape for a single "&".
        return self._text.get(key, default).replace("&&", "&")

    # -- tracks ----------------------------------------------------------
    def _build_tracks(self):
        raw = self.config.get(XML_PATH)
        if raw is None:
            raise GameDataError("%s not in CONFIG.MEG" % XML_PATH)
        xml = raw.decode("utf-8", "replace")
        try:
            blk = xml[xml.index("<MusicJukeboxTracksList>"):
                      xml.index("</MusicJukeboxTracksList>")]
        except ValueError:
            raise GameDataError("<MusicJukeboxTracksList> not found")

        def tag(body, name):
            m = re.search(r"<%s>\s*(.*?)\s*</%s>" % (name, name), body, re.S)
            return m.group(1).strip() if m else ""

        by_file = {}
        for name, size, offset in self.music.entries:
            by_file[name.split("\\")[-1].lower()] = (size, offset)

        tracks = []
        for _, body in re.findall(r'<entry\s+Name="([^"]+)"\s*>(.*?)</entry>',
                                  blk, re.S):
            fn = tag(body, "FileName")
            hit = by_file.get(fn.lower())
            if not hit:
                continue
            try:
                secs = int(tag(body, "TrackLengthSeconds") or 0)
            except ValueError:
                secs = 0
            tracks.append(Track(
                title=self.text(tag(body, "TextID"), fn),
                game=tag(body, "Game"),
                type=tag(body, "TrackType"),
                seconds=secs,
                bonus_locked=tag(body, "BonusContentUnlock").lower() == "true",
                filename=fn, size=hit[0], offset=hit[1]))

        # The jukebox lists tracks alphabetically by title.
        tracks.sort(key=lambda t: t.title.lower())
        return tracks

    def track_wav(self, track):
        return self.music.read(track.offset, track.size)

    # -- sound effects ---------------------------------------------------
    def sfx(self, stem, language=None):
        """One effect by its stem, e.g. "TDR_SFX_CONSTRU2".

        Spoken EVA lines live in SFX2D_<LANG>.MEG and carry a language suffix;
        the rest sit in SFX3D.MEG and SFX2D_ALL.MEG without one.  Returns the
        WAV bytes, or None.

        `language` asks for another language's recording of the same line.
        Steam downloads only the voice packs the title is set to, so a jukebox
        run with --lang for a language the installation does not carry finds
        nothing here, and English is the sensible stand-in.
        """
        lang = language or self.language
        for wanted in ("%s.WAV" % stem,
                       "%s\\%s_%s.WAV" % (lang, stem, lang)):
            for meg in self._sfx_archives(lang):
                raw = meg.get(wanted)
                if raw is not None:
                    return raw
        return None

    def _sfx_archives(self, language):
        """The archives that can hold one language's effects, opened once."""
        if language not in self._sfx_megs:
            out = []
            for name in ("SFX3D.MEG", "SFX2D_ALL.MEG", "SFX2D_%s.MEG" % language):
                path = os.path.join(self._data_dir, name)
                if os.path.isfile(path):
                    try:
                        out.append(Meg(path))
                    except GameDataError:
                        pass
            self._sfx_megs[language] = out
        return self._sfx_megs[language]

    def _sfx_list(self):
        """The sound archives, opened once and kept."""
        return self._sfx_archives(self.language)

    def texture_archive(self, filename):
        """One of the per-game texture archives, opened on first use."""
        if not hasattr(self, "_tex_cache"):
            self._tex_cache = {}
        if filename not in self._tex_cache:
            path = os.path.join(self._data_dir, filename)
            try:
                self._tex_cache[filename] = Meg(path) if os.path.isfile(path) else None
            except GameDataError:
                self._tex_cache[filename] = None
        return self._tex_cache[filename]

    # -- where the game keeps user content -------------------------------
    def user_dir(self):
        """The game's own Documents folder, inside the Proton prefix.

        Steam leaves this alone on updates, unlike the install directory, so
        exported tracks belong here rather than next to the archives.
        """
        marker = os.path.join("steamapps", "common", "CnCRemastered")
        root = self.game_dir
        if root.endswith(marker):
            base = root[:-len(marker)]
            pfx = os.path.join(base, "steamapps", "compatdata", "1213210",
                               "pfx", "drive_c", "users", "steamuser",
                               "Documents", "CnCRemastered")
            if os.path.isdir(pfx):
                return pfx
        return None

    def soundtrack_dir(self):
        """Where the exporter should put the tracks, creating nothing."""
        base = self.user_dir()
        if base:
            return os.path.join(base, "Soundtrack")
        music = os.path.expanduser("~/Music")
        for env in ("XDG_MUSIC_DIR",):
            if os.environ.get(env):
                music = os.environ[env]
        return os.path.join(music, "C&C Remastered Soundtrack")

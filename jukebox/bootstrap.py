# -*- coding: utf-8 -*-
"""Find an interpreter that can really run Qt, and hand over to it.

The program is started through a shebang, so it begins under whatever
`python3` happens to mean on the machine - and on a machine that uses uv,
pyenv or a packaged virtual environment, that is rarely the interpreter the
desktop's PyQt5 was installed for.  The old behaviour was to give up and
print "install python3-pyqt5", which on such a machine is wrong twice over:
the package is already there, just not on this interpreter's path.

So instead of insisting on one interpreter, this looks for one that works:

1.  This interpreter, if it can import PyQt5 and reach a platform plugin.
2.  Any other interpreter on the machine that can - the distro's own first,
    since that is where a distro's PyQt5 lives.
3.  Failing both, a private environment in the cache directory, with PyQt5
    from PyPI.  That one is self-contained, so it works anywhere, but it is
    a download and therefore the last resort rather than the first move.

The answer is remembered, so this costs nothing after the first run.

Importing PyQt5 is not on its own enough to call an interpreter usable: a
PyQt5 installed by pip against the system's Qt libraries imports perfectly
and still cannot open a window, because it carries no platform plugins and
reports an empty library path.  Where that is the only thing missing, it is
repaired here rather than held against the interpreter.
"""

import json
import locale
import os
import re
import shutil
import subprocess
import sys

APP = "cnc-jukebox"

# How often we have handed over already.  One hop is the normal case; a
# second means the remembered interpreter went stale and discovery ran
# again; beyond that something is wrong and guessing further would loop.
GUARD = "CNC_JUKEBOX_BOOTSTRAP"
MAX_HOPS = 2

# Escape hatches, for people who would rather decide themselves.
PYTHON_OVERRIDE = "CNC_JUKEBOX_PYTHON"
NO_VENV = "CNC_JUKEBOX_NO_VENV"

PYPI_PACKAGE = "PyQt5"
PROBE_TIMEOUT = 20
VENV_TIMEOUT = 600


# -- what to say when it goes wrong ------------------------------------------
# English is the base and the fallback; a translation is used only when the
# locale asks for it and the key exists.
MESSAGES = {
    "en": {
        "searching": "No Qt for this interpreter - looking for one that has it...",
        "handing_over": "Running under %(python)s, which has PyQt5.",
        "venv_making": ("No interpreter on this machine has a usable PyQt5.\n"
                        "Setting up a private environment in %(path)s\n"
                        "and installing %(package)s into it "
                        "(about 220 MB on disk, once)."),
        "venv_done": "Done.  Starting.",
        "venv_failed": "Could not set up that environment: %(reason)s",
        "no_qt": (
            "PyQt5 is required, and no interpreter on this machine has it.\n"
            "\n"
            "  Debian/Ubuntu/Mint:  sudo apt install python3-pyqt5\n"
            "  Fedora:              sudo dnf install python3-qt5\n"
            "  Arch:                sudo pacman -S python-pyqt5\n"
            "\n"
            "Already installed?  Then it belongs to another interpreter than\n"
            "the one `python3` points at here.  Name it directly:\n"
            "\n"
            "  %(override)s=/usr/bin/python3 %(app)s\n"),
        "no_venv": ("A private environment would have fixed this, but %(flag)s\n"
                    "is set, so none was made."),
    },
    "de": {
        "searching": "Kein Qt fuer diesen Interpreter - suche einen, der es hat ...",
        "handing_over": "Laeuft unter %(python)s, dort ist PyQt5 vorhanden.",
        "venv_making": ("Kein Interpreter auf diesem Rechner hat ein brauchbares "
                        "PyQt5.\nRichte eine eigene Umgebung in %(path)s ein\n"
                        "und installiere %(package)s hinein "
                        "(etwa 220 MB auf der Platte, einmalig)."),
        "venv_done": "Fertig.  Starte.",
        "venv_failed": "Diese Umgebung liess sich nicht einrichten: %(reason)s",
        "no_qt": (
            "PyQt5 wird benoetigt, und kein Interpreter auf diesem Rechner hat es.\n"
            "\n"
            "  Debian/Ubuntu/Mint:  sudo apt install python3-pyqt5\n"
            "  Fedora:              sudo dnf install python3-qt5\n"
            "  Arch:                sudo pacman -S python-pyqt5\n"
            "\n"
            "Schon installiert?  Dann gehoert es zu einem anderen Interpreter als\n"
            "dem, auf den `python3` hier zeigt.  Nenne ihn direkt:\n"
            "\n"
            "  %(override)s=/usr/bin/python3 %(app)s\n"),
        "no_venv": ("Eine eigene Umgebung haette das geloest, aber %(flag)s ist\n"
                    "gesetzt, also wurde keine angelegt."),
    },
}


def _language():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        tag = os.environ.get(var)
        if tag:
            break
    else:
        try:
            tag = locale.getdefaultlocale()[0] or ""
        except (ValueError, TypeError):
            tag = ""
    return (tag or "").split(":")[0].split(".")[0].replace("-", "_").split("_")[0].lower()


def say(key, **kw):
    """One message, in the user's language where there is one."""
    table = MESSAGES.get(_language(), MESSAGES["en"])
    text = table.get(key) or MESSAGES["en"][key]
    return text % kw if kw else text


def _note(key, **kw):
    sys.stderr.write(say(key, **kw) + "\n")
    sys.stderr.flush()


# -- is Qt usable from right here? -------------------------------------------
PLATFORM_PLUGIN = re.compile(r"^libq.*\.so$")


def _plugin_roots():
    """Directories that might hold Qt's own plugins, likeliest first."""
    roots = []
    for var in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_PLUGIN_PATH"):
        for part in (os.environ.get(var) or "").split(os.pathsep):
            if part:
                roots.append(part)
    try:
        import PyQt5
        here = os.path.dirname(os.path.abspath(PyQt5.__file__))
        roots += [os.path.join(here, "Qt5", "plugins"),
                  os.path.join(here, "Qt", "plugins")]
    except Exception:
        pass
    try:
        from PyQt5.QtCore import QCoreApplication, QLibraryInfo
        roots.append(QLibraryInfo.location(QLibraryInfo.PluginsPath))
        roots += [str(p) for p in QCoreApplication.libraryPaths()]
    except Exception:
        pass
    # Where the distributions put it.
    machine = os.uname().machine
    roots += ["/usr/lib/%s-linux-gnu/qt5/plugins" % machine,
              "/usr/lib64/qt5/plugins",
              "/usr/lib/qt5/plugins",
              "/usr/lib/%s-linux-gnu/qt5" % machine]
    return roots


def _has_platform_plugin(root):
    d = os.path.join(root, "platforms")
    try:
        return any(PLATFORM_PLUGIN.match(n) for n in os.listdir(d))
    except OSError:
        return False


def qt_usable_here():
    """True when this interpreter can open a Qt window.

    Repairs the plugin path on the way if that is all that stands in the
    way, which is the usual state of a pip-installed PyQt5 sitting on the
    system's own Qt libraries.
    """
    try:
        import PyQt5.QtWidgets                                  # noqa: F401
    except Exception:
        return False
    for root in _plugin_roots():
        if not _has_platform_plugin(root):
            continue
        old = os.environ.get("QT_PLUGIN_PATH") or ""
        if root not in old.split(os.pathsep):
            os.environ["QT_PLUGIN_PATH"] = \
                os.pathsep.join([root] + [p for p in old.split(os.pathsep) if p])
        try:
            from PyQt5.QtCore import QCoreApplication
            QCoreApplication.addLibraryPath(root)
        except Exception:
            pass
        return True
    return False


def probe():
    """Entry point for the probe run in a candidate interpreter."""
    if not qt_usable_here():
        raise SystemExit(1)
    sys.stdout.write(os.environ.get("QT_PLUGIN_PATH", ""))
    raise SystemExit(0)


# -- looking around the machine ----------------------------------------------
def _package_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _candidates():
    """Interpreters worth asking, the most promising first."""
    out = []

    def add(path):
        if not path:
            return
        path = shutil.which(path) if not os.path.isabs(path) else path
        if path and os.access(path, os.X_OK) and path not in out:
            out.append(path)

    add(os.environ.get(PYTHON_OVERRIDE))
    # The distribution's own interpreter first: a distribution's PyQt5 is
    # installed for that one, and it is the one a packaged python shadows.
    add("/usr/bin/python3")
    add("/usr/local/bin/python3")
    add("python3")
    for minor in range(15, 7, -1):
        add("/usr/bin/python3.%d" % minor)
        add("python3.%d" % minor)
    seen, unique = set(), []
    for path in out:
        key = os.path.realpath(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _ask(python):
    """Does that interpreter have a usable Qt?  -> its plugin path, or None."""
    code = ("import sys; sys.path.insert(0, %r);"
            "from jukebox.bootstrap import probe; probe()" % _package_dir())
    try:
        done = subprocess.run([python, "-c", code], cwd="/", timeout=PROBE_TIMEOUT,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.decode("utf-8", "replace").strip()


# -- remembering the answer --------------------------------------------------
def _cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, APP)


def _cache_file():
    return os.path.join(_cache_dir(), "interpreter.json")


def _remember(python, plugin_path):
    try:
        os.makedirs(_cache_dir(), exist_ok=True)
        with open(_cache_file(), "w", encoding="utf-8") as f:
            json.dump({"python": python, "qt_plugin_path": plugin_path}, f, indent=1)
    except OSError:
        pass            # a cache that cannot be written only costs a search


def _recall():
    try:
        with open(_cache_file(), encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return None
    python = saved.get("python")
    if python and os.access(python, os.X_OK):
        return python, saved.get("qt_plugin_path") or ""
    return None


def forget():
    try:
        os.unlink(_cache_file())
    except OSError:
        pass


# -- the private environment, when nothing else has Qt -----------------------
def _venv_python():
    return os.path.join(_cache_dir(), "venv", "bin", "python3")


def _build_venv():
    """A virtual environment with PyQt5 from PyPI.  Returns its interpreter.

    PyPI's PyQt5 brings its own Qt and its own plugins, so this works on a
    machine that has no Qt at all - which is the only situation that gets
    this far.  No system packages are inherited: a half-installed PyQt5
    outside is exactly what we are stepping around.
    """
    if os.environ.get(NO_VENV):
        _note("no_venv", flag=NO_VENV)
        return None
    target = os.path.join(_cache_dir(), "venv")
    python = _venv_python()
    if os.access(python, os.X_OK) and _ask(python) is not None:
        return python
    _note("venv_making", path=target, package=PYPI_PACKAGE)
    base = None
    for candidate in _candidates():
        try:
            if subprocess.run([candidate, "-c", "import venv"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0:
                base = candidate
                break
        except (OSError, subprocess.SubprocessError):
            continue
    if base is None:
        _note("venv_failed", reason="python3 -m venv")
        return None
    try:
        os.makedirs(_cache_dir(), exist_ok=True)
        subprocess.run([base, "-m", "venv", target], check=True,
                       timeout=VENV_TIMEOUT)
        subprocess.run([python, "-m", "pip", "install", "--upgrade", "--quiet",
                        PYPI_PACKAGE], check=True, timeout=VENV_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        _note("venv_failed", reason=str(e))
        return None
    _note("venv_done")
    return python if _ask(python) is not None else None


# -- putting it together -----------------------------------------------------
def _hand_over(python, plugin_path, quiet=False):
    env = dict(os.environ)
    env[GUARD] = str(int(os.environ.get(GUARD, "0")) + 1)
    if plugin_path:
        env["QT_PLUGIN_PATH"] = plugin_path
    script = sys.argv[0]
    if not os.path.isfile(script):
        script = shutil.which(script) or script
    script = os.path.abspath(script)
    if not quiet:
        _note("handing_over", python=python)
    os.execve(python, [python, script] + sys.argv[1:], env)


def ensure_qt():
    """Make sure the process we end up in can run Qt, or explain why not."""
    if qt_usable_here():
        return
    hops = int(os.environ.get(GUARD, "0") or "0")
    if hops >= MAX_HOPS:
        forget()
        _note("no_qt", override=PYTHON_OVERRIDE, app=APP)
        raise SystemExit(1)

    if hops == 0:
        remembered = _recall()
        if remembered:
            _hand_over(remembered[0], remembered[1], quiet=True)
    else:
        forget()                 # the remembered one did not work out

    _note("searching")
    for python in _candidates():
        if os.path.realpath(python) == os.path.realpath(sys.executable):
            continue             # already know this one cannot
        plugin_path = _ask(python)
        if plugin_path is not None:
            _remember(python, plugin_path)
            _hand_over(python, plugin_path)

    python = _build_venv()
    if python:
        plugin_path = _ask(python) or ""
        _remember(python, plugin_path)
        _hand_over(python, plugin_path)

    _note("no_qt", override=PYTHON_OVERRIDE, app=APP)
    raise SystemExit(1)

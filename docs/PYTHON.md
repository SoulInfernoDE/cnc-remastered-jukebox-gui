# Finding an interpreter that has Qt

***English** · [Deutsch](PYTHON.de.md)*

The jukebox starts through a shebang, so it begins under whatever `python3`
happens to mean on the machine. On a machine that uses uv, pyenv or a packaged
virtual environment, that is rarely the interpreter the desktop's PyQt5 was
installed for — and the old behaviour was to give up and print "install
python3-pyqt5", which on such a machine is wrong twice over: the package is
already there, just not on this interpreter's path.

---

## What it actually looks like

Measured on a Linux Mint 22.3 machine with uv installed:

| Interpreter | Version | PyQt5 |
| --- | --- | --- |
| `python3` → `~/.local/bin/python3` → uv's CPython | 3.15.0 | **no** |
| `/usr/bin/python3` | 3.12.3 | yes |

uv had put its own `python3` ahead of the system's on `PATH`. Nothing was
broken and nothing was missing; the two simply never met.

There is a second trap behind the first. On that machine PyQt5 is a pip
install living in `~/.local/lib/python3.12/site-packages`, bound against the
system's own Qt libraries, and it carries no Qt plugins of its own:

```
>>> QCoreApplication.libraryPaths()
[]
>>> QApplication(sys.argv)
This application failed to start because no Qt platform plugin could be initialized.
```

It imports perfectly and still cannot open a window. **Importing PyQt5 is
therefore not proof that an interpreter is usable**, which is why the check
here goes one step further and makes sure a platform plugin can actually be
reached.

## What happens now

1. **This interpreter**, if it can import PyQt5 and reach a platform plugin.
   Where the plugin path is the only thing missing — the case above — it is
   repaired by pointing `QT_PLUGIN_PATH` at a plugin directory that exists,
   and nothing else happens at all.
2. **Any other interpreter on the machine.** The distribution's own is asked
   first, since that is where a distribution's PyQt5 lives and it is the one a
   packaged python shadows. Each candidate is asked in a subprocess, which
   answers whether it can import PyQt5 *and* where its plugins are. The first
   that can is handed the program through `execve`.
3. **A private environment**, in `~/.cache/cnc-jukebox/venv`, with PyQt5 from
   PyPI. That copy brings its own Qt and its own plugins, so it works on a
   machine with no Qt at all — but it is a download, which is why it is the
   last resort rather than the first move.

The answer is written to `~/.cache/cnc-jukebox/interpreter.json` and reused, so
the search happens once:

```
cold start, searching and handing over    0.76 s
warm start, straight to the remembered one 0.27 s
building the private environment          22.5 s, 217 MB on disk
```

If the remembered interpreter stops working — removed, upgraded, Qt uninstalled
— the second attempt throws the note away and searches again. A counter in the
environment stops that after two hops, so a machine where nothing works gets a
message rather than a loop.

## Deciding yourself

```bash
CNC_JUKEBOX_PYTHON=/usr/bin/python3 ./cnc-jukebox   # use this one
CNC_JUKEBOX_NO_VENV=1 ./cnc-jukebox                 # never build an environment
rm -rf ~/.cache/cnc-jukebox                         # forget and search again
```

## Why not simply put everything in a venv

Because on the machine above PyQt5 was already installed and working. Starting
with an environment of its own would have downloaded a second copy of Qt and
spent 217 MB to replace something that was one path away — and it would have
done so on every machine, including the many where the distribution's package
is exactly right. The environment is the right answer for a machine that has no
Qt; it is the wrong answer for a machine that merely has it somewhere else.

## The exporter is not affected

The [exporter](https://github.com/SoulInfernoDE/cnc-remastered-jukebox-trackexport),
which is its own program in a repository of its own, uses nothing but the
standard library, so any interpreter runs it — including uv's. It was checked
under CPython 3.15 and reads all 203 tracks correctly.

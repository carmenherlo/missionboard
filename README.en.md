# missionboard

[Español](README.md) · **English**

A family app for a shared tablet. Kids follow their **missions** (short lists of
steps, with pictures and voice), earn **stars**, spend them in a **shop** and unlock
a **daily prize** with a spinning wheel. **Routines** guide the busy moments of the
day (getting ready for school, bedtime) with an alarm, a talking clock and music.
A **parents' zone**, behind a code, is where everything is set up.

The interface is in Spanish; the code, comments and tests are in English.

## Features

- **Kids' screens:** each child has a colour and an avatar; their day is a route of
  missions, each one opened as a panel of steps to tick. Stars, a celebration when
  a mission is done, and a daily prize when all of them are.
- **Routines:** parts with their minutes, one after the other, between an alarm and
  a goal. Either the start or the end time is pinned and the rest falls into place.
  On screen: a clock with each part's stretch, a voice that says what comes next,
  warnings before a part ends, a ten-second countdown, each kid with their mission,
  and music playing over chosen parts. Routines can ring at a time or be started by
  hand.
- **Parents' zone:** children, missions and templates, routines (with a trial mode
  that runs them faster and lets you set the kids' missions at will), prizes, shop,
  the parents' code, an event log (CSV export) and **backups**.
- **Natural voice:** sentences are spoken with [Piper](https://github.com/OHF-Voice/piper1-gpl)
  on the server and cached; the tablet's own voice is the fallback.
- **Works offline:** no external services at run time; fonts and images are bundled.

## Quick start

Requirements: Python 3.12.

```bash
python -m venv .venv && source .venv/bin/activate   # or a conda environment
pip install -r requirements.txt -r requirements-dev.txt
MISSIONBOARD_DATA_DIR=personal uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Open <http://localhost:8002/>. The default parents' code is **1234**: change it in
*Configurar → Código de padres*.

`bash dev.sh` does the same with a conda environment named `missionboard` and
prints the address to open from a tablet on the same network.

### The natural voice (optional)

Without a voice model the app uses the device's speech synthesis. To use Piper,
put [`es_ES-sharvard-medium.onnx`](https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium)
and its `.onnx.json` in `personal/voices/`, or point `MISSIONBOARD_VOICE_MODEL` at the
`.onnx` file. The Docker image downloads it on build.

## Docker

```bash
docker compose up -d --build
```

The app listens on port 8003 and keeps its data in `./personal` (mounted at `/srv/data`).

## Data

Everything the family sets up and does lives in one folder (`MISSIONBOARD_DATA_DIR`,
`personal/` by default), never in the repository:

| Path | What |
|---|---|
| `config.yaml` | Children, missions, templates, routines, prizes, shop, settings and feature switches |
| `missionboard.db` | SQLite: the history (steps ticked, missions done, stars, prizes, purchases, routines run, event log) |
| `photos/`, `sounds/`, `backgrounds/` | Uploaded photos, songs, and the background illustration of each moment of the day |
| `voice-cache/` | Spoken sentences, generated again when missing |

- **Migrations** run on start-up; the previous file is kept next to it
  (`config.yaml.vN.bak`, `missionboard.db.vN.bak`). A file from a newer version stops
  the app instead of being changed.
- **Backups:** *Configurar → Copia de seguridad* downloads everything in one `.zip`
  (configuration, history, photos, songs, backgrounds) and restores such a file,
  checking it first and keeping what there was in `backups/`. It is the way to move
  a family to another device.
- `settings` and `features` in `config.yaml` can be edited by hand; invalid values
  stop the app at start-up with a message.

## Tests

```bash
pytest
```

Tests go through the HTTP API and the services. One of them fails if a colour is
written outside `app/static/css/tokens.css`.

## Project layout

```
app/
  main.py                 the FastAPI app: routers, shared state, start-up checks
  <feature>/              children, missions, templates, today, routines, prizes,
                          shop, songs, events, backup, voice…
    api.py                routes: HTTP and validation
    service.py            rules, plain Python
    repository.py         reading and writing YAML or SQLite
  storage/                config.yaml store and migrations, SQLite and migrations
  static/                 the front end: HTML, CSS and JavaScript modules, no build step
    css/tokens.css        every colour, size and timing (themes/ holds Material colour roles)
    js/screens/           one module per screen
themes/                   Material Theme Builder exports
tools/                    theme and image-library generators
tests/
```

Back end: FastAPI, PyYAML, SQLite. Front end: plain HTML, CSS and JavaScript modules,
without frameworks or bundlers.

## Third-party assets

| | Licence |
|---|---|
| [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) (`app/static/libraries/fluent/`) | MIT, see `LICENSE-fluent-emoji.txt` |
| Spanish keywords from [Unicode CLDR](https://cldr.unicode.org/) | Unicode License, see `LICENSE-unicode-cldr.txt` |
| [Nunito](https://fonts.google.com/specimen/Nunito) (`app/static/fonts/nunito/`) | SIL Open Font License, see `OFL.txt` |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) (`piper-tts`, installed with pip) | See its repository |
| Voice model `es_ES-sharvard-medium` (downloaded, not in the repository) | See its [model card](https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium) |

## Licence

[MIT](LICENSE). The third-party assets in the table above keep their own licences.

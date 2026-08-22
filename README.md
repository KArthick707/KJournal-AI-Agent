# journal-ai-agent

A local AI journal: type or speak whatever's on your mind, and it gets turned
into a structured, readable journal entry you can browse and search later.

- **Write** — type freely in the browser and save.
- **Speak** — record with your microphone; live speech-to-text (via the
  browser's built-in Web Speech API) shows a running transcript as you talk,
  which you can edit before saving. The audio itself is saved alongside the
  entry so you can play it back later.
- **Upload audio** — attach an existing voice memo file. Auto-transcription
  isn't available for uploaded files (see *Known limitations* below), so you
  can optionally type a transcript alongside it.

Whatever text comes in (typed, spoken, or manually transcribed) is sent to
Claude once, which turns raw, rambling input into a titled entry: a cleaned-up
body (fixed grammar, organized paragraphs, filler words removed, but still in
your own voice), a one-sentence summary, a mood label, and a few topic tags.
Everything is stored locally in SQLite — nothing leaves your machine except
that one structuring call to the Anthropic API.

## Design

Single-call structuring, not an agent loop: turning a raw transcript into a
titled/summarized/tagged entry is one extraction step with nothing to
investigate and no tools to call, so `journal/agent.py` makes one
`client.messages.parse()` call with a Pydantic schema and returns. If no
`ANTHROPIC_API_KEY` is configured, saving still works — the entry is stored
with the raw text as its body instead of blocking on a missing key.

## Security

This app has no login and is meant to be used by one person, on their own
machine. That model only holds as long as the server stays loopback-only, so
a few things enforce and account for that:

- **No cross-site writes.** A browser attaches `Origin` to POST requests
  whether or not they're cross-site, and unlike the request body, a page
  can't forge it — so any request with an `Origin` that doesn't match the
  server's own is rejected (403). Without this, any website you have open in
  the same browser could silently POST fake entries (or run up your Claude
  API bill) purely because the server trusted every request that reached it.
- **Binding beyond loopback requires an explicit opt-in.** Setting
  `JOURNAL_HOST` to anything other than `127.0.0.1`/`localhost` refuses to
  start unless `JOURNAL_ALLOW_REMOTE=1` is also set — because there's still
  no login, so a non-loopback host means anyone on your network can read,
  write, and hear your journal. Set that only if you've deliberately decided
  you want it reachable that way.
- **Uploaded audio is stored under a validated extension**, not whatever the
  uploading client claims — an unrecognized extension is normalized to
  `.bin` so it can never later be served back with a browser-guessed
  `Content-Type` like `text/html`.
- **`/audio/{filename}` only serves filenames matching the exact format this
  app generates** (a hex UUID + a known extension), rather than trying to
  blocklist specific bad characters.

## Known limitations

- **Uploaded audio files are not auto-transcribed.** The only way to get a
  live transcript is the **Speak** tab's in-browser recording, which relies
  on the Web Speech API (Chrome/Edge; not supported in Firefox — recording
  still works there, but you'd type the transcript yourself). Adding real
  speech-to-text for arbitrary uploaded audio would mean wiring in a separate
  transcription service/API, which felt like more than this first version
  needed.
- Search is a plain SQL substring match across title/body/summary/tags — fine
  for one person's journal, but it won't do fuzzy or semantic search.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional — entries save unstructured without it
```

## Usage

```bash
python -m journal
```

Then open `http://127.0.0.1:8000` in your browser. Voice recording needs
microphone permission, which browsers only grant on `localhost`/`127.0.0.1`
or HTTPS — the default host already satisfies that.

## Windows desktop app

`desktop_app.py` runs the same app inside a native window (via
[pywebview](https://pywebview.flowrz.com/), using Windows' built-in WebView2
runtime) instead of a browser tab, and `journalagent.spec` packages it into a
single `JournalAgent.exe` with [PyInstaller](https://pyinstaller.org/).

There's no Windows machine in this project's dev loop, so the `.exe` is built
by CI, not locally:

1. Push to this branch (or run the **Build Windows app** workflow manually
   from the Actions tab — "Run workflow").
2. Once it finishes, open the workflow run and download the
   `JournalAgent-windows` artifact — that's `JournalAgent.exe`.
3. Double-click it. It starts the server in the background (data saved to
   `%APPDATA%\JournalAIAgent`, not a temp folder) and opens a window pointed
   at it.

To build it yourself instead:

```bash
pip install -r requirements-desktop.txt
pyinstaller journalagent.spec
```

**Untested caveat:** the **Speak** tab's live transcription relies on the
browser's Web Speech API. In a real Chrome/Edge tab this works because those
are official Google/Microsoft builds with a speech backend baked in — plain
open-source Chromium (e.g. what Electron bundles) doesn't have one, so voice
transcription silently fails there. WebView2 is built on the same engine as
Edge and *should* carry the same working speech backend, but I have no
Windows machine to actually confirm that — audio recording and playback
should work regardless either way, since those don't depend on the speech
service. If transcription doesn't work in the packaged app, that's the first
thing to check.

## Configuration

All environment variables are optional; see `journal/config.py` for defaults.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Optional. Claude API key; without it, entries save with raw text instead of a structured version. |
| `JOURNAL_MODEL` | Model override (default `claude-opus-5`). |
| `JOURNAL_HOST` / `JOURNAL_PORT` | Where the local web app listens (default `127.0.0.1:8000`). |
| `JOURNAL_DATA_DIR` | Where the SQLite database and saved audio files live (default `./data`). |
| `JOURNAL_MAX_AUDIO_BYTES` | Cap on a single uploaded/recorded audio file (default 100MB). |
| `JOURNAL_ALLOW_REMOTE` | Required (`1`/`true`) to start with a non-loopback `JOURNAL_HOST` — see *Security* above. |

## Tests

```bash
pip install pytest httpx
python -m pytest tests/ -v
```

Tests cover the SQLite storage layer directly, `agent.py`'s structuring call
with the Anthropic client mocked, and `app.py`'s request-level behavior
(cross-site rejection, audio validation, host guard) via FastAPI's
`TestClient` — no network calls, no real LLM calls.

## What's next

This is a fresh scaffold, not a finished product. Natural next steps: real
speech-to-text for uploaded audio files, entry editing/deletion, exporting
the journal (Markdown/PDF), and a simple "ask your journal" Q&A mode over
past entries (similar in spirit to this author's
[soc-analyst-agent](https://github.com/KArthick707/soc-analyst-agent) log
copilot, grounded in actual past entries instead of invented ones).

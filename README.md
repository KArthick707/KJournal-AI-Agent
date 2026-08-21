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

## Configuration

All environment variables are optional; see `journal/config.py` for defaults.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Optional. Claude API key; without it, entries save with raw text instead of a structured version. |
| `JOURNAL_MODEL` | Model override (default `claude-opus-5`). |
| `JOURNAL_HOST` / `JOURNAL_PORT` | Where the local web app listens (default `127.0.0.1:8000`). |
| `JOURNAL_DATA_DIR` | Where the SQLite database and saved audio files live (default `./data`). |

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

Tests cover the SQLite storage layer directly and `agent.py`'s structuring
call with the Anthropic client mocked — no network calls, no real LLM calls.

## What's next

This is a fresh scaffold, not a finished product. Natural next steps: real
speech-to-text for uploaded audio files, entry editing/deletion, exporting
the journal (Markdown/PDF), and a simple "ask your journal" Q&A mode over
past entries (similar in spirit to this author's
[soc-analyst-agent](https://github.com/KArthick707/soc-analyst-agent) log
copilot, grounded in actual past entries instead of invented ones).

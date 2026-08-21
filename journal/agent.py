"""Turns a raw typed/spoken-word transcript into a structured journal entry.

This is a single extraction/rewrite call, not an agent loop -- there's
nothing to investigate and no tools to call, just one text-in/JSON-out
transform, so it uses client.messages.parse() directly rather than a
tool-calling loop."""

from pydantic import BaseModel

from . import config

MAX_TOKENS = 4096

SYSTEM_PROMPT = (
    "You turn a raw, unedited journal entry -- typed or transcribed from speech -- "
    "into a well-structured one. Preserve the author's own voice, meaning, and every "
    "detail they actually said; never invent events, feelings, or details that "
    "aren't there. Clean up filler words ('um', 'like', false starts) and fix "
    "grammar, and organize rambling speech into coherent paragraphs, but keep it "
    "first-person and personal, not corporate or clinical. Then produce: a short "
    "evocative title (under 8 words), a one-sentence summary, a one-or-two-word "
    "mood label (e.g. 'anxious', 'content', 'excited'), and up to 5 short topic tags."
)


class JournalDraft(BaseModel):
    title: str
    body: str
    summary: str
    mood: str
    tags: list[str]


class AgentNotConfigured(RuntimeError):
    """Raised when no Anthropic API key is configured."""


def _build_client():
    """Test seam: constructing the Anthropic client."""
    import anthropic

    return anthropic.Anthropic()


def structure_entry(raw_text: str) -> JournalDraft:
    """Calls Claude once to turn raw_text into a JournalDraft. Callers should
    catch AgentNotConfigured and fall back to saving the raw text unstructured
    rather than blocking the save on having an API key."""
    if not config.has_api_key():
        raise AgentNotConfigured(
            "Entry structuring requires an Anthropic API key. Set the ANTHROPIC_API_KEY environment variable."
        )

    client = _build_client()
    response = client.messages.parse(
        model=config.get_model(),
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
        output_format=JournalDraft,
    )
    return response.parsed_output

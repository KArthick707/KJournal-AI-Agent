import pytest

from journal import agent


def test_structure_entry_raises_when_not_configured(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(agent.AgentNotConfigured):
        agent.structure_entry("today was a good day")


def test_structure_entry_returns_parsed_draft(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    expected = agent.JournalDraft(
        title="A Good Day",
        body="Today was a good day. I went for a walk and felt calm.",
        summary="A calm, pleasant day.",
        mood="content",
        tags=["walk", "calm"],
    )

    class FakeResponse:
        parsed_output = expected

    class FakeMessages:
        def parse(self, **kwargs):
            assert kwargs["output_format"] is agent.JournalDraft
            assert kwargs["messages"] == [
                {"role": "user", "content": "today was a good day, went for a walk"}
            ]
            return FakeResponse()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(agent, "_build_client", lambda: FakeClient())

    draft = agent.structure_entry("today was a good day, went for a walk")
    assert draft is expected
    assert draft.mood == "content"
    assert draft.tags == ["walk", "calm"]

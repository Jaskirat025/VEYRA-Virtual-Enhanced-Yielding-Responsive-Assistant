from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_notes_roundtrip(database):
    note_id = database.save_note("Shopping", "milk and coffee")
    assert note_id > 0
    results = database.search_notes("coffee")
    assert results and results[0]["title"] == "Shopping"
    assert database.search_notes("nothing-here") == []


def test_messages_and_conversations(database):
    conversation = database.ensure_conversation(None, title="First")
    database.add_message(conversation, "user", "hello")
    database.add_message(conversation, "assistant", "hi")
    messages = database.messages(conversation)
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert database.conversations()[0]["message_count"] == 2
    assert database.ensure_conversation(conversation) == conversation


def test_tool_log_is_persisted_and_parsed(database):
    database.log_tool_call(
        conversation_id="c1",
        step=1,
        tool="calcola",
        category="calc",
        risk="safe",
        args_redacted={"espressione": "2+2"},
        status="ok",
        duration_ms=3,
        output_preview="4",
    )
    entries = database.tool_log()
    assert len(entries) == 1
    assert entries[0]["args_redacted"]["espressione"] == "2+2"
    assert entries[0]["status"] == "ok"


def test_timers_become_due(database):
    past = (datetime.now(UTC) - timedelta(seconds=5)).isoformat(timespec="seconds")
    database.add_timer("tea", past)
    due = database.due_timers()
    assert len(due) == 1
    database.complete_timer(due[0]["id"])
    assert database.due_timers() == []


def test_kv_store(database):
    assert database.get_value("onboarded") == ""
    database.set_value("onboarded", "1")
    assert database.get_value("onboarded") == "1"
    database.set_value("onboarded", "2")
    assert database.get_value("onboarded") == "2"

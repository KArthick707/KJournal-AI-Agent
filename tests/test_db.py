from journal import db


def _conn():
    conn = db.connect(":memory:")
    db.init_db(conn)
    return conn


def test_create_and_get_entry_roundtrip():
    conn = _conn()
    entry = db.create_entry(
        conn,
        source="typed",
        raw_text="raw",
        title="Title",
        body="Body text",
        summary="Summary",
        mood="calm",
        tags=["a", "b"],
        audio_path=None,
        structured=True,
    )
    fetched = db.get_entry(conn, entry["id"])
    assert fetched["title"] == "Title"
    assert fetched["tags"] == ["a", "b"]
    assert fetched["structured"] is True


def test_get_entry_missing_returns_none():
    conn = _conn()
    assert db.get_entry(conn, 999) is None


def test_list_entries_orders_newest_first():
    conn = _conn()
    db.create_entry(conn, source="typed", raw_text="one", title="One", body="one")
    db.create_entry(conn, source="typed", raw_text="two", title="Two", body="two")
    entries = db.list_entries(conn)
    assert [e["title"] for e in entries] == ["Two", "One"]


def test_list_entries_search_matches_body():
    conn = _conn()
    db.create_entry(conn, source="typed", raw_text="raw", title="Alpha", body="mentions dogs")
    db.create_entry(conn, source="typed", raw_text="raw", title="Beta", body="mentions cats")
    results = db.list_entries(conn, query="dogs")
    assert len(results) == 1
    assert results[0]["title"] == "Alpha"


def test_list_entries_respects_limit_and_offset():
    conn = _conn()
    for i in range(5):
        db.create_entry(conn, source="typed", raw_text=str(i), title=f"E{i}", body="x")
    page1 = db.list_entries(conn, limit=2, offset=0)
    page2 = db.list_entries(conn, limit=2, offset=2)
    assert [e["title"] for e in page1] == ["E4", "E3"]
    assert [e["title"] for e in page2] == ["E2", "E1"]


def test_untagged_entry_defaults_to_empty_list_and_unstructured():
    conn = _conn()
    entry = db.create_entry(conn, source="typed", raw_text="raw", title="No tags", body="body")
    assert entry["tags"] == []
    assert entry["structured"] is False

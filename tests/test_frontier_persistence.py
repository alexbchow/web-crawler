import pytest
from crawler.frontier import Frontier


def test_urls_written_to_queue_table(tmp_path):
    db = str(tmp_path / "frontier.db")
    f = Frontier(db_path=db)
    f.add("http://example.com/a")
    f.add("http://example.com/b")

    rows = f.con.execute("SELECT url FROM queue").fetchall()
    assert {r[0] for r in rows} == {"http://example.com/a", "http://example.com/b"}


def test_record_fetch_moves_url_to_seen_table(tmp_path):
    db = str(tmp_path / "frontier.db")
    f = Frontier(db_path=db)
    f.add("http://example.com/a")
    f.record_fetch("http://example.com/a")

    queue_rows = f.con.execute("SELECT url FROM queue").fetchall()
    seen_rows = f.con.execute("SELECT url FROM seen").fetchall()
    assert queue_rows == []
    assert seen_rows[0][0] == "http://example.com/a"


def test_resume_restores_queue(tmp_path):
    db = str(tmp_path / "frontier.db")

    f1 = Frontier(db_path=db, resume=False)
    f1.add("http://example.com/a")
    f1.add("http://example.com/b")

    f2 = Frontier(db_path=db, resume=True)
    assert "http://example.com/a" in f2.seen
    assert "http://example.com/b" in f2.seen
    assert not f2.is_empty()


def test_resume_preserves_fifo_order(tmp_path):
    db = str(tmp_path / "frontier.db")

    f1 = Frontier(db_path=db, resume=False)
    f1.add("http://example.com/a")
    f1.add("http://example.com/b")
    f1.add("http://example.com/c")

    f2 = Frontier(db_path=db, resume=True)
    assert f2.next() == "http://example.com/a"
    assert f2.next() == "http://example.com/b"
    assert f2.next() == "http://example.com/c"


def test_resume_does_not_re_add_seen_urls(tmp_path):
    db = str(tmp_path / "frontier.db")

    f1 = Frontier(db_path=db, resume=False)
    f1.add("http://example.com/a")
    f1.record_fetch("http://example.com/a")  # mark as done

    f2 = Frontier(db_path=db, resume=True)
    f2.add("http://example.com/a")  # should be a no-op — already in seen
    assert f2.is_empty()


def test_no_resume_wipes_previous_state(tmp_path):
    db = str(tmp_path / "frontier.db")

    f1 = Frontier(db_path=db, resume=False)
    f1.add("http://example.com/a")

    f2 = Frontier(db_path=db, resume=False)  # fresh start
    assert f2.is_empty()
    assert len(f2.seen) == 0

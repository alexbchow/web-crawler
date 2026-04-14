from crawler.frontier import Frontier


def test_is_empty_on_init():
    f = Frontier()
    assert f.is_empty() is True


def test_add_makes_not_empty():
    f = Frontier()
    f.add("http://example.com")
    assert f.is_empty() is False


def test_next_returns_url():
    f = Frontier()
    f.add("http://example.com")
    assert f.next() == "http://example.com"


def test_next_on_empty_returns_none():
    f = Frontier()
    assert f.next() is None


def test_fifo_ordering():
    f = Frontier()
    f.add("http://a.com")
    f.add("http://b.com")
    f.add("http://c.com")
    assert f.next() == "http://a.com"
    assert f.next() == "http://b.com"
    assert f.next() == "http://c.com"


def test_duplicate_not_added():
    f = Frontier()
    f.add("http://example.com")
    f.add("http://example.com")
    f.next()
    assert f.next() is None


def test_already_crawled_url_not_readded():
    # A URL that was popped and crawled should not re-enter the queue
    f = Frontier()
    f.add("http://example.com")
    f.next()  # simulate crawling it
    f.add("http://example.com")  # try to re-add
    assert f.is_empty() is True


def test_is_empty_after_all_consumed():
    f = Frontier()
    f.add("http://example.com")
    f.next()
    assert f.is_empty() is True

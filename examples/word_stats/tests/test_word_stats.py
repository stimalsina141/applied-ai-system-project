from word_stats import summary, word_count


def test_simple_sentence():
    assert word_count("the quick fox") == 3


def test_extra_spaces_are_not_words():
    assert word_count("the  quick   fox ") == 3


def test_empty_text_has_no_words():
    assert word_count("") == 0


def test_summary_text():
    assert summary("hello there world") == "Words: 3"

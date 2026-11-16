def word_count(text):
    """Count the words in a piece of text."""
    return len(text.split())


def summary(text):
    """Return a one-line summary like 'Words: 3'."""
    return "Words: " + str(word_count(text))

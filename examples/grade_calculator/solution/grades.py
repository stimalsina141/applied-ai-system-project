def letter_grade(score):
    """Turn a 0-100 score into a letter. 90 and above is an A."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


def class_average(scores):
    """Return the average of a list of scores."""
    total = 0
    for i in range(len(scores)):
        total += scores[i]
    return total / len(scores)

from fractions import Fraction
from app.modules.overlaps.sweep import spans


def union_length(rows):
    intervals = [(Fraction(row['start']), Fraction(row['end']), index) for index, row in enumerate(rows)]
    return sum((right-left for left, right, _ in spans(intervals)), start=Fraction(0))

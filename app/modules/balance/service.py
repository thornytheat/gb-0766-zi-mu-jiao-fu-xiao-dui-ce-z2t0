from fractions import Fraction
from app.rational import show
from .coverage import union_length


def balance(cues, mapped, overlaps, rejected):
    total = dict(original=Fraction(0), delivered=Fraction(0), removed=Fraction(0), pending=Fraction(0))
    rows = []
    for track in sorted({row['track'] for row in cues}):
        pieces = [row for row in mapped if row['track'] == track]
        exact = dict(original=union_length([row for row in cues if row['track'] == track]))
        for name, kind in [('delivered', 'KEEP'), ('removed', 'REMOVE'), ('pending', 'GAP')]:
            exact[name] = union_length([row for row in pieces if row['kind'] == kind])
        for name, number in exact.items():
            total[name] += number
        rows.append(dict(track=track, **{name: show(value) for name, value in exact.items()}))
    gap = total['original'] - total['delivered'] - total['removed'] - total['pending']
    return dict(rows=rows, counts=dict(**{name: show(value) for name, value in total.items()},
                                     rejected_unmeasurable=rejected, overlap_target_frames=overlaps),
                balanced=gap == 0, difference=show(gap))

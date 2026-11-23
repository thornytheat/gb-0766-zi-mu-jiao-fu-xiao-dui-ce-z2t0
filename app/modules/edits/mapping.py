from bisect import bisect_right
from fractions import Fraction
from math import ceil
from app.modules.clock.timecode import RATIO
from app.rational import show


def map_cues(cues, edit_list):
    endpoints = [edit['end'] for edit in edit_list]
    fragments = []
    for cue in cues:
        cursor, end = Fraction(cue['start']), Fraction(cue['end'])
        for edit in edit_list[bisect_right(endpoints, cursor):]:
            if edit['start'] >= end:
                break
            left, right = max(cursor, edit['start']), min(end, edit['end'])
            if cursor < left:
                fragments.append(fragment(cue, cursor, left, None))
            fragments.append(fragment(cue, left, right, edit))
            cursor = right
        if cursor < end:
            fragments.append(fragment(cue, cursor, end, None))
    return dict(rows=fragments, cuts=edit_list,
                counts={kind: sum(row['kind'] == kind for row in fragments) for kind in ('KEEP', 'REMOVE', 'GAP')})


def fragment(cue, start, end, edit):
    kind = edit['kind'] if edit else 'GAP'
    result = dict(cue_id=cue['cue_id'], track=cue['track'], line=cue['line'], text=cue['text'],
                  start=show(start), end=show(end), kind=kind, cut=edit['cut'] if edit else None,
                  cut_line=edit['line'] if edit else None)
    if kind == 'KEEP':
        left = edit['target'] + (start - edit['start']) * RATIO
        right = edit['target'] + (end - edit['start']) * RATIO
        result.update(target_start=show(left), target_end=show(right), frame_in=ceil(left), frame_out=ceil(right))
    return result

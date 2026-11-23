from collections import defaultdict
from .account import account
from .reader import tabulate

FIELDS = ('cue_id', 'track', 'format', 'in', 'out', 'text')
MISSING = {'', '-', 'N/A', 'NULL', '未知'}
ALIASES = {'legacy_id': 'cue_id', 'time_in': 'in', 'time_out': 'out'}


def receive(text):
    rows, isolated, headings, blanks, data_lines = tabulate(text, ALIASES, FIELDS)
    groups = defaultdict(list)
    for row in rows:
        if any(row[key] in MISSING for key in FIELDS):
            isolated.append(dict(row, code='MISSING'))
        else:
            groups[row['track'], row['cue_id']].append(row)
    cues, copies = [], []
    for group in groups.values():
        if len({tuple(row[key] for key in FIELDS) for row in group}) > 1:
            isolated.extend(dict(row, code='CUE_CONFLICT') for row in group)
        else:
            cues.append(group[0])
            copies.extend(dict(row, code='CUE_COPY') for row in group[1:])
    return dict(rows=cues, isolated=sorted(isolated, key=lambda row: row['line']), copies=copies,
                counts=account(cues, isolated, copies, headings, blanks, data_lines))

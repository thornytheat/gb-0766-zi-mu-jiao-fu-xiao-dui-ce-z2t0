from app.rational import show
from .timecode import RATIO, position


def validate(cues):
    valid, isolated = [], []
    for cue in cues:
        try:
            start, end = [position(cue[k], cue['format']) for k in ('in', 'out')]
            if start >= end:
                raise ValueError('TIME_ORDER')
        except ValueError as error:
            isolated.append(dict(cue, code=str(error)))
            continue
        valid.append(dict(cue, start=show(start), end=show(end), nominal_start=show(start * RATIO), nominal_end=show(end * RATIO)))
    return dict(rows=valid, isolated=isolated, counts=dict(valid=len(valid), isolated=len(isolated)))

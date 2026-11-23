from collections import defaultdict
from .sweep import spans


def locate(fragments):
    groups = defaultdict(list)
    for row in fragments:
        if row['kind'] == 'KEEP':
            groups[row['track']].append((row['frame_in'], row['frame_out'], (row['line'], row['cue_id'])))
    rows = []
    for track, intervals in sorted(groups.items()):
        for left, right, active in spans(intervals):
            if len(active) > 1:
                rows.append(dict(track=track, frame_in=left, frame_out=right, frames=right-left,
                                 lines=[value[0] for value in active], cues=[value[1] for value in active], code='OVERLAP'))
    return dict(rows=rows, counts=dict(regions=len(rows), overlap_frames=sum(row['frames'] for row in rows)))

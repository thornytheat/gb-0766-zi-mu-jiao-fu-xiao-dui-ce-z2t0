from app.material import example
from app.modules.overlaps.service import locate
from app.pipeline import inspect


def fragment(line, start, end, track='zh'):
    return dict(kind='KEEP', track=track, frame_in=start, frame_out=end, line=line, cue_id=str(line))


# TRAP-23

def test_touch_is_not_overlap():
    assert locate([fragment(1,0,10), fragment(2,10,20)])['counts']['regions'] == 0


def test_triple_overlap_once(dirty):
    row, = [r for r in dirty['overlaps']['rows'] if len(r['lines'])==3]
    assert (row['frames'], row['lines']) == (28, [2,3,17])


def test_total_overlap(dirty):
    assert dirty['overlaps']['counts'] == dict(regions=7, overlap_frames=65)


def test_two_tracks_never_mix():
    assert inspect(example('clean'))['overlaps']['counts']['overlap_frames'] == 0


def test_subframe_empty_interval_ignored():
    assert locate([fragment(1,7,7), fragment(2,6,8)])['rows'] == []


def test_big_id_in_collision(dirty):
    assert dirty['overlaps']['rows'][-1]['cues'] == ['9007199254740993', 'C108']


def test_reordered_cut_boundary_retains_same_cue():
    result = locate([fragment(1,10,20), fragment(1,0,10), fragment(2,12,14)])
    assert [(row['frame_in'], row['frame_out'], row['lines']) for row in result['rows']] == [(12, 14, [1,2])]

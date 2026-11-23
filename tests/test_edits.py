import pytest
from app.modules.edits.contract import timeline
from app.problems import Rejection


def test_cross_cut_retains_source_line(dirty):
    assert [(x['kind'], x['line'], x['start'], x['end']) for x in dirty['edits']['rows'] if x['cue_id']=='C101'] == [
        ('KEEP',2,'900','1000'), ('REMOVE',2,'1000','1200'), ('KEEP',2,'1200','1300')]


def test_unknown_gap(dirty):
    row, = [x for x in dirty['edits']['rows'] if x['kind']=='GAP']
    assert (row['cue_id'], row['start'], row['end'], row['cut_line']) == ('C103','2000','2200',None)


def test_edl_source_collision():
    with pytest.raises(Rejection) as error:
        timeline('cut,start,end,target,kind\nA,1,100,0,KEEP\nB,99,110,,REMOVE\n')
    assert error.value.code == 'CUT_OVERLAP'


def test_edl_target_collision():
    with pytest.raises(Rejection) as error:
        timeline('cut,start,end,target,kind\nA,1,100,0,KEEP\nB,100,110,50,KEEP\n')
    assert error.value.code == 'TARGET_OVERLAP'


def test_cut_target_anchor(dirty):
    row = next(x for x in dirty['edits']['rows'] if x['cue_id']=='C101' and x['cut']=='B-01')
    assert (row['frame_in'], row['frame_out'], row['cut_line']) == (810,891,4)


def test_remove_has_no_target(dirty):
    assert all('frame_in' not in row for row in dirty['edits']['rows'] if row['kind']=='REMOVE')

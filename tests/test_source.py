import pytest
from app.modules.source.service import receive
from app.problems import Rejection


# TRAP-02, TRAP-17

def test_bom_and_alias(dirty):
    assert dirty['source']['rows'][0]['cue_id'] == 'C101'


# TRAP-04

def test_repeated_header(dirty):
    assert dirty['source']['counts']['headings'] == 2
    assert dirty['source']['counts']['data_lines'] == 23


# TRAP-05, TRAP-07

def test_width_and_missing(dirty):
    assert {(row['line'], row['code']) for row in dirty['source']['isolated']} >= {(13, 'MISSING'), (16, 'WIDTH')}


# TRAP-09

def test_string_identity(dirty):
    assert dirty['source']['rows'][5]['cue_id'] == '9007199254740993'


# TRAP-14

def test_conflicting_revision(dirty):
    assert [(r['line'], r['text']) for r in dirty['source']['isolated'] if r['code'] == 'CUE_CONFLICT'] == [(14, '文字被改写'), (15, '不同供应稿')]


def test_duplicate_delivery(dirty):
    assert [(r['line'], r['cue_id']) for r in dirty['source']['copies']] == [(9, 'C101')]


def test_only_header():
    with pytest.raises(Rejection) as error:
        receive('cue_id,track,format,in,out,text\n')
    assert error.value.code == 'HEADER_ONLY'

from fractions import Fraction
import pytest
from app.modules.clock.timecode import position


def test_illegal_drop_label(dirty):
    assert [(row['cue_id'], row['code']) for row in dirty['clock']['isolated']] == [('C105', 'DROPPED_LABEL')]


# TRAP-10

def test_exact_rate(dirty):
    row = next(r for r in dirty['clock']['rows'] if r['cue_id'] == 'C104')
    assert (row['start'], row['end'], row['nominal_start']) == ('1800', '1810', '36036/25')


def test_tenth_minute_label_is_legal():
    assert position('00:10:00;00', 'DF') == 17982


def test_label_jump_is_one_frame():
    assert position('00:01:00;02', 'DF') - position('00:00:59;29', 'DF') == 1


def test_wall_time_formats_agree():
    assert position('00:30.030', 'VTT') == position('00:00:30,030', 'SRT') == 900


def test_ndf_does_not_skip():
    assert position('00:01:00:00', 'NDF') == Fraction(1800)


def test_format_separator_strict():
    with pytest.raises(ValueError, match='TIME_LABEL'):
        position('00:01:00;02', 'NDF')

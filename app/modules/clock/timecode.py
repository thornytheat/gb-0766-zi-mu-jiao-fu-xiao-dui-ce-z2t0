import re
from fractions import Fraction

SOURCE_RATE = Fraction(30000, 1001)
TARGET_RATE = Fraction(24)
RATIO = TARGET_RATE / SOURCE_RATE
SMPTE = re.compile(r'([0-9]{2}):([0-5][0-9]):([0-5][0-9])([:;])([0-2][0-9])')
WALL = {'SRT': re.compile(r'([0-9]{2}):([0-5][0-9]):([0-5][0-9]),([0-9]{3})'),
        'VTT': re.compile(r'(?:(\d{2}):)?([0-5][0-9]):([0-5][0-9])\.([0-9]{3})')}


def position(label, mode):
    if mode == 'FRAME' and re.fullmatch(r'[0-9]{1,12}', label):
        return Fraction(label)
    if mode in WALL:
        match = WALL[mode].fullmatch(label)
        if match:
            hh, mm, ss, ms = (int(value or 0) for value in match.groups())
            return (3600 * hh + 60 * mm + ss + Fraction(ms, 1000)) * SOURCE_RATE
    if mode in ('DF', 'NDF'):
        match = SMPTE.fullmatch(label)
        if match and match[4] == (';' if mode == 'DF' else ':'):
            hh, mm, ss, frame = (int(match[i]) for i in (1, 2, 3, 5))
            minute = hh * 60 + mm
            if mode == 'DF' and mm % 10 and ss == 0 and frame < 2:
                raise ValueError('DROPPED_LABEL')
            skipped = 2 * (minute - minute // 10) if mode == 'DF' else 0
            return Fraction((minute * 60 + ss) * 30 + frame - skipped)
    raise ValueError('TIME_LABEL')

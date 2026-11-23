from app.modules.source.reader import tabulate
from app.problems import Rejection

FIELDS = ('cue_id', 'track', 'format', 'in', 'out', 'text')
WITH_BASELINE = FIELDS + ('baseline',)


def read_patch(text):
    """解析只含改动行的补丁 CSV。表头与字幕原件同构，可多带一列 baseline。

    返回 (rows, rejected, baseline)。baseline 为补丁内声明的母版档号（可空）。
    """
    try:
        rows, rejected, _, _, _ = tabulate(text, {}, WITH_BASELINE)
        declared = {row['baseline'] for row in rows if row['baseline']}
        if len(declared) > 1:
            raise Rejection('PATCH_BASELINE', '补丁各行声明的母版档号不一致')
        for row in rows:
            row.pop('baseline', None)
        return rows, rejected, next(iter(declared), None)
    except Rejection as wide_error:
        if wide_error.code != 'HEADER':
            raise
        rows, rejected, _, _, _ = tabulate(text, {}, FIELDS)
        return rows, rejected, None

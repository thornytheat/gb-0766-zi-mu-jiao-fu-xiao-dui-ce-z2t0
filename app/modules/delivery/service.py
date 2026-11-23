from .checks import verify

CODES = {'MISSING': '必填字段缺失', 'WIDTH': '列数不符', 'CUE_CONFLICT': '同轨同号内容冲突',
         'CUE_COPY': '相同字幕副本', 'TIME_LABEL': '时码格式无效', 'DROPPED_LABEL': '该帧号已跳过',
         'TIME_ORDER': '出点不晚于入点', 'OVERLAP': '同轨目标帧相交', 'GAP': '缺少切版记录'}


def signing(record):
    return dict(verified=True, certificate=verify(record), **record, reason_codes=CODES)

HEADERS = {
    'source': ('line', 'cue_id', 'format', 'in', 'out', 'code', 'text'),
    'clock': ('line', 'cue_id', 'in', 'out', 'start', 'end', 'nominal_start', 'code'),
    'edits': ('line', 'cue_id', 'start', 'end', 'cut', 'kind', 'frame_in', 'frame_out'),
    'overlaps': ('frame_in', 'frame_out', 'frames', 'track', 'cues', 'lines', 'code'),
    'balance': ('track', 'original', 'delivered', 'removed', 'pending'),
    'runs': ('id', 'version', 'created_at', 'elapsed_us'),
    'patches': ('line', 'cue_id', 'track', 'in', 'out', 'patch_state', 'reason', 'text'),
    'delivery': ('field', 'hash'),
}
LABELS = {'line': '原行', 'cue_id': '字幕号', 'format': '格式', 'in': '原入点', 'out': '原出点', 'code': '原因',
          'text': '字幕文本', 'start': '源入帧', 'end': '源出帧', 'nominal_start': '折算入帧', 'cut': '切段',
          'kind': '分段判定', 'frame_in': '目标入帧', 'frame_out': '目标出帧', 'frames': '重叠帧',
          'track': '轨道', 'cues': '字幕号', 'lines': '原行组', 'original': '原覆盖', 'delivered': '交付覆盖',
          'removed': '剪辑移除', 'pending': '缺段待证', 'id': '归档档号', 'version': '规则版本',
          'created_at': '生成 UTC', 'elapsed_us': '耗时 μs', 'field': '原件', 'hash': 'SHA-256',
          'patch_state': '落版状态', 'reason': '待定/拒收原因'}


def cells(stages, sheet, archive, stamp):
    if sheet == 'runs':
        return archive.inventory()
    if sheet == 'patches':
        block = stages.get('patches')
        if not block:
            return []
        open_rows = [dict(row, line=row.get('line', 0)) for row in
                     block.get('pending', []) + block.get('rejected', [])]
        open_rows.sort(key=lambda row: (row.get('line', 0), str(row.get('cue_id', ''))))
        effective_rows = [row for row in stages['source']['rows']
                          if row.get('patch_state') == 'EFFECTIVE']
        return open_rows + effective_rows
    if sheet == 'delivery':
        if not stamp:
            return []
        if stamp.get('kind') == 'patch':
            return [dict(field='补丁原件', hash=stamp['patch_sha256']),
                    dict(field='声明基线', hash=stamp['baseline_sha256']),
                    dict(field='落版结果', hash=stamp['result_sha256'])]
        return [dict(field=key, hash=value) for key, value in stamp['input_sha256'].items()]
    view = stages[sheet]
    return view.get('isolated', []) + view.get('copies', []) + view.get('rows')

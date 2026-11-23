import csv
from collections import defaultdict
from io import StringIO
from app.digests import digest, encode
from app.modules.source.service import FIELDS, MISSING
from app.pipeline import inspect

EFFECTIVE = 'EFFECTIVE'
PENDING = 'PENDING'
REJECTED = 'REJECTED'
UNCHANGED = 'UNCHANGED'

STATE_LABELS = {EFFECTIVE: '已生效', PENDING: '待定', REJECTED: '拒收', UNCHANGED: '未改'}
REASON_LABELS = {
    'DRIFT': '补丁基线已被改过',
    'UNKNOWN_CUE': '母版中找不到该字幕号',
    'ISOLATED_MASTER': '该字幕在母版中为隔离行',
    'BAD_TIMECODE': '补丁行时码无法核算，保留母版原行',
    'PATCH_CONFLICT': '同一份补丁内同轨同号互相冲突',
    'MISSING': '补丁行必填字段缺失',
    'WIDTH': '补丁行列数不符',
}


def cue_fingerprint(cue):
    return digest(encode([cue[key] for key in FIELDS]))


def fp_key(track, cue_id):
    return f'{track}\x1f{cue_id}'


def landing_fingerprints(record):
    """某份档案落版字幕的逐句指纹快照。"""
    if record['manifest'].get('kind') == 'patch':
        return dict(record['cue_fingerprints'])
    return {fp_key(cue['track'], cue['cue_id']): cue_fingerprint(cue)
            for cue in record['stages']['source']['rows']}


def master_index(master):
    """落版档案已采信行按 (轨道, 字幕号) 建索引；隔离行单独登记。"""
    live = {(cue['track'], cue['cue_id']): cue for cue in master['stages']['source']['rows']}
    isolated = {(cue.get('track'), cue.get('cue_id'))
                for cue in master['stages']['source']['isolated']
                if cue.get('track') is not None and cue.get('cue_id') is not None}
    return live, isolated


def merge(tip, patch_rows, patch_rejected, expected_fingerprints):
    """把补丁逐行接到链尖档案上。

    内容级判定在此完成：拒收（缺字段、坏列宽、补丁内冲突）、待定（撞基线、
    无落版行、母版隔离行）、生效（整行替换）。撞基线 = 该句在供应商声明基线
    上的指纹与链尖当前指纹不一致。未被触及的行保持未改。
    时码核算留给重跑阶段，坏时码会在那里退回原行并转为待定。
    """
    live, isolated_keys = master_index(tip)
    current_fingerprints = landing_fingerprints(tip)
    merged = {key: dict(cue) for key, cue in live.items()}
    effective, pending, rejected = [], [], []

    for row in patch_rejected:
        values = dict(zip(FIELDS, row['raw']))
        rejected.append(dict(values, line=row['line'], state=REJECTED, reason=row['code']))

    groups = defaultdict(list)
    for cue in patch_rows:
        if any(cue.get(key) in MISSING for key in FIELDS):
            rejected.append(dict(cue, state=REJECTED, reason='MISSING'))
        else:
            groups[cue['track'], cue['cue_id']].append(cue)

    for key, versions in sorted(groups.items()):
        distinct = {tuple(row[k] for k in FIELDS) for row in versions}
        if len(distinct) > 1:
            rejected.extend(dict(row, state=REJECTED, reason='PATCH_CONFLICT') for row in versions)
            continue
        patch_cue = versions[0]
        if key not in live:
            reason = 'ISOLATED_MASTER' if key in isolated_keys else 'UNKNOWN_CUE'
            pending.append(dict(patch_cue, state=PENDING, reason=reason))
            continue
        if expected_fingerprints.get(fp_key(*key)) != current_fingerprints.get(fp_key(*key)):
            pending.append(dict(patch_cue, state=PENDING, reason='DRIFT'))
            continue
        tip_cue = live[key]
        merged[key] = dict(patch_cue, line=tip_cue['line'], raw=tip_cue['raw'])
        effective.append(dict(patch_cue, line=tip_cue['line'], state=EFFECTIVE,
                              replaced=current_fingerprints[fp_key(*key)],
                              previous_text=tip_cue['text']))

    return merged, effective, pending, rejected


def _render_csv(merged):
    buf = StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(FIELDS)
    for cue in merged.values():
        writer.writerow([cue[k] for k in FIELDS])
    return buf.getvalue()


def landing(tip, merged, effective, pending, rejected):
    """用落版字幕重跑整条校对链，撞帧与覆盖账按新内容重算。

    重跑后若某条已生效行时码不合法，落版退回原行，该行改判待定，
    保证同一句不会出现正文新、时间旧的半行状态。
    """
    live, _ = master_index(tip)
    material = dict(cues=_render_csv(merged), cuts=tip['original']['cuts'])
    stages = inspect(material)
    bad_time = {(row['track'], row['cue_id']): row['code']
                for row in stages['clock']['isolated']}
    effective_keys = {(row['track'], row['cue_id']) for row in effective}
    reverted = []
    for key in list(effective_keys):
        if key in bad_time:
            patch_cue = merged[key]
            merged[key] = dict(live[key])
            reverted.append(dict(patch_cue, state=PENDING, reason='BAD_TIMECODE', detail=bad_time[key]))
    if reverted:
        material = dict(cues=_render_csv(merged), cuts=tip['original']['cuts'])
        stages = inspect(material)
    pending = pending + reverted

    changed = {key for key in merged if key in effective_keys and key not in bad_time}
    for row in stages['source']['rows']:
        key = (row['track'], row['cue_id'])
        row['patch_state'] = EFFECTIVE if key in changed else UNCHANGED

    stages['patches'] = dict(
        effective=effective, pending=pending, rejected=rejected,
        counts=dict(effective=len(changed), pending=len(pending), rejected=len(rejected),
                    unchanged=len(stages['source']['rows']) - len(changed),
                    signable=not pending and not rejected))
    stages['balance']['counts']['pending_cues'] = len(pending)
    stages['balance']['counts']['rejected_patch_rows'] = len(rejected)
    stages['balance']['counts']['signable'] = not pending and not rejected
    return stages, merged, material

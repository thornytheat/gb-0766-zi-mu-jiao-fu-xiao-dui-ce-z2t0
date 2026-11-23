from datetime import datetime, timezone
from app.digests import digest, encode, fingerprints
from app.problems import Rejection
from .ledger import cue_fingerprint, fp_key, landing, landing_fingerprints, merge
from .reader import read_patch


def _read_archive(store, key, absent_code, absent_text):
    try:
        return store.read(key)
    except Rejection as error:
        if error.code == 'NO_RUN':
            raise Rejection(absent_code, absent_text, 404)
        raise


def resolve_record(master_store, patch_store, key):
    """档号可能指向母版，也可能指向补丁链上的某一跳。"""
    if (patch_store.root / f'{key}.json').exists():
        record = patch_store.read(key)
        if record['manifest'].get('kind') == 'patch':
            return record, 'patch'
    record = _read_archive(master_store, key, 'NO_BASELINE', '补丁基线档案不存在')
    return record, 'master'


def apply_patch(master_store, patch_store, body):
    patch_text = body['patch'] if isinstance(body, dict) and isinstance(body.get('patch'), str) else None
    if patch_text is None:
        raise Rejection('PAYLOAD', '提交补丁 CSV 文本')
    patch_rows, patch_rejected, declared_key = read_patch(patch_text)
    baseline_key = body.get('baseline') or declared_key
    if not baseline_key:
        raise Rejection('PATCH_BASELINE', '补丁未声明母版档号')
    if declared_key and declared_key != baseline_key:
        raise Rejection('PATCH_BASELINE', '补丁声明的母版档号与提交基线不一致')

    declared, declared_kind = resolve_record(master_store, patch_store, baseline_key)
    # 链尖：声明基线若是补丁，沿其链尾找到最新一跳；若是母版，链尖为该母版最新补丁。
    tip, tip_kind = _chain_tip(master_store, patch_store, declared, declared_kind)

    # 供应商在声明基线上看到的逐句指纹；与链尖当前指纹比对即可识别撞基线。
    expected_fingerprints = landing_fingerprints(declared)
    merged, effective, pending, rejected = merge(tip, patch_rows, patch_rejected, expected_fingerprints)
    stages, merged_cues, landing_material = landing(tip, merged, effective, pending, rejected)

    cue_fingerprints = {fp_key(key[0], key[1]): cue_fingerprint(cue)
                        for key, cue in merged_cues.items()}
    hashes = fingerprints({'patch': patch_text, 'baseline': baseline_key})
    # 同一补丁接在同一链尖上重试：键不变、不新增版本；链尖已前进则是新的一跳。
    tip_hash = digest(encode(cue_fingerprints))
    key = digest(encode(['patch', hashes, tip_hash]))
    result_hash = digest(encode(stages))
    rule_version = tip['manifest'].get('version') or tip['manifest'].get('rule_version')
    manifest = dict(id=key, kind='patch', rule_version=rule_version,
                    baseline_id=baseline_key, baseline_kind=declared_kind,
                    tip_id=tip['manifest']['id'], tip_kind=tip_kind,
                    patch_sha256=hashes['patch'], baseline_sha256=hashes['baseline'],
                    result_sha256=result_hash,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    signable=stages['balance']['counts']['signable'])
    chain = tip.get('chain', [tip['manifest']['id']]) + [key]
    record = dict(manifest=manifest, patch=dict(cues=patch_text), original=landing_material,
                  stages=stages, cue_fingerprints=cue_fingerprints, chain=chain)
    actual, reused = patch_store.publish(key, record)
    if not reused and digest(encode(actual['stages'])) != result_hash:
        raise Rejection('DRIFT', '补丁复算与已归档结果不一致', 409)
    if reused:
        # 同一补丁在同一链尖重试：直接采信已归档证据，不新增版本、不重写时间戳。
        manifest = actual['manifest']
        stages = actual['stages']
    return dict(id=key, reused=reused, manifest=manifest,
                counts=stages['patches']['counts'], chain=actual['chain'])


def _chain_tip(master_store, patch_store, declared, declared_kind):
    """找到声明基线所在链的最新一跳。"""
    if declared_kind == 'master':
        root_id = declared['manifest']['id']
        candidates = []
        for path in patch_store.root.glob('*.json'):
            entry = patch_store.read(path.stem)
            if entry['manifest'].get('kind') == 'patch' and entry['chain'][0] == root_id:
                candidates.append(entry)
        if not candidates:
            return declared, 'master'
        tip = max(candidates, key=lambda entry: (entry['manifest']['created_at'], entry['manifest']['id']))
        return tip, 'patch'
    # 声明基线本身是补丁：链尾即引用了它的最新一跳，没有则它自己就是链尖。
    root_id = declared['chain'][0]
    candidates = []
    for path in patch_store.root.glob('*.json'):
        entry = patch_store.read(path.stem)
        if entry['manifest'].get('kind') == 'patch' and entry['chain'][0] == root_id:
            candidates.append(entry)
    tip = max(candidates, key=lambda entry: (entry['manifest']['created_at'], entry['manifest']['id']))
    return tip, 'patch'


def patch_summary(record):
    return dict(id=record['manifest']['id'], manifest=record['manifest'],
                counts=record['stages']['patches']['counts'])

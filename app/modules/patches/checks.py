from app.digests import digest, encode
from app.problems import Rejection


def verify_patch(record):
    """补丁证据核验：散列勾稽之外，待定项存在即禁止签发。"""
    stamp = record['manifest']
    if stamp.get('kind') != 'patch':
        raise Rejection('NO_PATCH', '补丁档案不存在', 404)
    if digest(record['patch']['cues'].encode()) != stamp['patch_sha256']:
        raise Rejection('INVALID_EVIDENCE', '补丁原件散列不符', 409)
    if digest(encode(record['stages'])) != stamp['result_sha256']:
        raise Rejection('INVALID_EVIDENCE', '补丁落版结果被篡改', 409)
    if not record['stages']['balance']['counts']['signable']:
        raise Rejection('PENDING_BLOCK', '仍有待定或拒收行，补丁不能签发', 409)
    return stamp

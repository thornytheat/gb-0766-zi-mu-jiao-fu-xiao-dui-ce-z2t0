import pytest
from app.digests import digest, encode
from app.material import example
from app.modules.patches.checks import verify_patch
from app.modules.patches.ledger import EFFECTIVE, PENDING, REJECTED, UNCHANGED, merge, landing, master_index
from app.modules.patches.reader import read_patch
from app.modules.patches.service import apply_patch
from app.problems import Rejection

PATCH_HEADER = 'cue_id,track,format,in,out,text\n'


def patch_csv(*rows):
    return PATCH_HEADER + ''.join(','.join(row) + '\n' for row in rows)


@pytest.fixture
def master(client):
    return client.post('/api/runs', json={'sample': 'clean'}).json


@pytest.fixture
def stores(client):
    ext = client.application.extensions
    return ext['cut_archive'], ext['patch_archive']


def test_effective_patch_replaces_master_row(stores, master):
    master_store, patch_store = stores
    patch = patch_csv(('C02', '简中', 'FRAME', '200', '250', '他收起修订后的地图'))
    outcome = apply_patch(master_store, patch_store, {'patch': patch, 'baseline': master['id']})
    assert outcome['counts'] == dict(effective=1, pending=0, rejected=0, unchanged=3, signable=True)
    record = patch_store.read(outcome['id'])
    landed = {row['cue_id']: row for row in record['stages']['source']['rows']}
    assert landed['C02']['text'] == '他收起修订后的地图'
    assert landed['C02']['patch_state'] == EFFECTIVE
    assert landed['C01']['patch_state'] == UNCHANGED


def test_retry_same_patch_creates_no_new_version(stores, master):
    master_store, patch_store = stores
    payload = {'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '今天风很轻')),
               'baseline': master['id']}
    first = apply_patch(master_store, patch_store, payload)
    again = apply_patch(master_store, patch_store, payload)
    assert again['reused'] and again['id'] == first['id']
    assert len(list(patch_store.root.glob('*.json'))) == 1


def test_overlap_and_balance_recomputed_on_new_content(stores, master):
    master_store, patch_store = stores
    before = master_store.read(master['id'])['stages']['balance']['counts']
    # 把 C02 拉长到与 C03（源帧 1000 起）相接并制造同轨相交
    patch = patch_csv(('C02', '简中', 'FRAME', '200', '1050', '他收起地图并走向巷口'))
    outcome = apply_patch(master_store, patch_store, {'patch': patch, 'baseline': master['id']})
    record = patch_store.read(outcome['id'])
    after = record['stages']['balance']['counts']
    assert record['stages']['overlaps']['counts']['overlap_frames'] > 0
    assert after['original'] != before['original']
    assert after['signable'] is True


def test_unknown_cue_stays_pending_and_blocks_signing(stores, master):
    master_store, patch_store = stores
    patch = patch_csv(('C404', '简中', 'FRAME', '10', '20', '母版没有的句子'))
    outcome = apply_patch(master_store, patch_store, {'patch': patch, 'baseline': master['id']})
    assert outcome['counts']['pending'] == 1 and outcome['manifest']['signable'] is False
    record = patch_store.read(outcome['id'])
    pending, = record['stages']['patches']['pending']
    assert (pending['cue_id'], pending['reason']) == ('C404', 'UNKNOWN_CUE')
    with pytest.raises(Rejection, match='待定'):
        verify_patch(record)


def test_bad_timecode_reverts_to_master_and_marks_pending(stores, master):
    master_store, patch_store = stores
    original = {row['cue_id']: row for row in master_store.read(master['id'])['stages']['source']['rows']}
    patch = patch_csv(('C02', '简中', 'DF', '00:99:00:00', '00:01:00:00', '坏时码新文本'))
    outcome = apply_patch(master_store, patch_store, {'patch': patch, 'baseline': master['id']})
    record = patch_store.read(outcome['id'])
    pending, = record['stages']['patches']['pending']
    assert pending['reason'] == 'BAD_TIMECODE'
    landed = {row['cue_id']: row for row in record['stages']['source']['rows']}
    # 落版退回母版整行，不会留下正文新、时间旧的半行
    assert landed['C02']['text'] == original['C02']['text']
    assert landed['C02']['in'] == original['C02']['in']


def test_patch_internal_conflict_is_rejected(stores, master):
    master_store, patch_store = stores
    patch = patch_csv(
        ('C01', '简中', 'FRAME', '100', '140', '版本甲'),
        ('C01', '简中', 'FRAME', '100', '140', '版本乙'))
    outcome = apply_patch(master_store, patch_store, {'patch': patch, 'baseline': master['id']})
    assert outcome['counts']['rejected'] == 2
    record = patch_store.read(outcome['id'])
    assert {row['reason'] for row in record['stages']['patches']['rejected']} == {'PATCH_CONFLICT'}
    assert record['manifest']['signable'] is False


def test_missing_field_and_width_rejected(stores, master):
    master_store, patch_store = stores
    text = PATCH_HEADER + 'C03,简中,FRAME,,1100,缺入点\nC01,简中,FRAME,100,140,多一列,EXTRA\n'
    outcome = apply_patch(master_store, patch_store, {'patch': text, 'baseline': master['id']})
    record = patch_store.read(outcome['id'])
    reasons = {row['reason'] for row in record['stages']['patches']['rejected']}
    assert reasons == {'MISSING', 'WIDTH'}


def test_drift_detected_when_baseline_cue_changed(stores, master):
    master_store, patch_store = stores
    first = apply_patch(master_store, patch_store, {
        'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '第一跳改写')),
        'baseline': master['id']})
    # 第二份补丁仍声明旧母版为基线，但 C01 已被第一跳改过
    stale = apply_patch(master_store, patch_store, {
        'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '基于旧母版的改写')),
        'baseline': master['id']})
    record = patch_store.read(stale['id'])
    pending, = record['stages']['patches']['pending']
    assert pending['reason'] == 'DRIFT'
    # 接上一跳（最新基线）则不再撞基线
    fresh = apply_patch(master_store, patch_store, {
        'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '基于新基线的改写')),
        'baseline': first['id']})
    assert fresh['counts']['pending'] == 0 and fresh['counts']['effective'] == 1


def test_patch_chain_keeps_every_version_recoverable(stores, master):
    master_store, patch_store = stores
    one = apply_patch(master_store, patch_store, {
        'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '第一版')),
        'baseline': master['id']})
    two = apply_patch(master_store, patch_store, {
        'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '第二版')),
        'baseline': one['id']})
    record_two = patch_store.read(two['id'])
    assert record_two['chain'] == [master['id'], one['id'], two['id']]
    # 母版原件与第一跳证据都仍在，旧版可恢复
    assert master_store.read(master['id'])['original']['cues'].startswith('cue_id')
    first = patch_store.read(one['id'])
    assert '第一版' in first['patch']['cues']
    assert first['manifest']['id'] != two['id']


def test_master_evidence_never_overwritten(stores, master):
    master_store, patch_store = stores
    before = digest(encode(master_store.read(master['id'])))
    apply_patch(master_store, patch_store, {
        'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '改写')),
        'baseline': master['id']})
    assert digest(encode(master_store.read(master['id']))) == before
    # 补丁档与母版档分目录存放
    assert patch_store.root != master_store.root


def test_patch_csv_baseline_column(stores, master):
    master_store, patch_store = stores
    text = f'cue_id,track,format,in,out,text,baseline\nC01,简中,FRAME,100,140,带基线列,{master["id"]}\n'
    outcome = apply_patch(master_store, patch_store, {'patch': text})
    assert outcome['counts']['effective'] == 1
    rows, rejected, declared = read_patch(text)
    assert declared == master['id'] and rejected == []


def test_baseline_mismatch_rejected(stores, master):
    master_store, patch_store = stores
    text = 'cue_id,track,format,in,out,text,baseline\nC01,简中,FRAME,100,140,x,' + '0' * 64 + '\n'
    with pytest.raises(Rejection, match='基线档案不存在'):
        apply_patch(master_store, patch_store, {'patch': text})
    with pytest.raises(Rejection, match='声明的母版档号'):
        apply_patch(master_store, patch_store, {'patch': text, 'baseline': master['id']})


def test_verify_hashes_catch_tampering(stores, master):
    master_store, patch_store = stores
    outcome = apply_patch(master_store, patch_store, {
        'patch': patch_csv(('C01', '简中', 'FRAME', '100', '140', '可签发版')),
        'baseline': master['id']})
    record = patch_store.read(outcome['id'])
    assert verify_patch(record)['signable'] is True
    record['stages']['overlaps']['counts']['overlap_frames'] = 999
    with pytest.raises(Rejection, match='篡改'):
        verify_patch(record)


def test_merge_helper_states(stores, master):
    from app.modules.patches.ledger import landing_fingerprints
    master_store, _ = stores
    base = master_store.read(master['id'])
    live, isolated = master_index(base)
    assert ('简中', 'C01') in live and not isolated
    rows, rejected = read_patch(patch_csv(('C404', '简中', 'FRAME', '1', '2', '无主')))[:2]
    merged, effective, pending, rejected = merge(base, rows, rejected, landing_fingerprints(base))
    assert pending[0]['reason'] == 'UNKNOWN_CUE'
    assert merged[('简中', 'C01')]['cue_id'] == 'C01'


def test_patch_routes(client, master):
    response = client.post('/api/patches', json={
        'patch': patch_csv(('C02', '简中', 'FRAME', '200', '250', '接口改写')),
        'baseline': master['id']})
    assert response.status_code == 200
    key = response.json['id']
    assert client.get(f'/api/patches/{key}').json['counts']['effective'] == 1
    assert client.get(f'/api/patches/{key}/landing').json['counts']['signable'] is True
    cert = client.get(f'/api/patches/{key}/certificate')
    assert cert.status_code == 200 and cert.json['certificate']['kind'] == 'patch'
    export = client.get(f'/api/patches/{key}/export')
    assert export.status_code == 200 and 'attachment;' in export.headers['Content-Disposition']
    assert client.get('/api/patches').json['count'] == 1


def test_pending_patch_certificate_denied_over_http(client, master):
    response = client.post('/api/patches', json={
        'patch': patch_csv(('C404', '简中', 'FRAME', '1', '2', '无主')),
        'baseline': master['id']})
    key = response.json['id']
    denied = client.get(f'/api/patches/{key}/certificate')
    assert (denied.status_code, denied.json['code']) == (409, 'PENDING_BLOCK')


def test_patch_sheet_renders(client, master):
    key = client.post('/api/patches', json={
        'patch': patch_csv(('C02', '简中', 'FRAME', '200', '250', '页面改写')),
        'baseline': master['id']}).json['id']
    html = client.get(f'/sheet/patches?run={key}').get_data(as_text=True)
    assert '补丁落版' in html and '已生效' in html and '下载补丁证据' in html


def test_bad_payload(client, master):
    assert client.post('/api/patches', json={}).status_code == 422
    assert client.post('/api/patches', json={'patch': 'x'}).status_code == 422


def test_seven_column_baseline_conflict(client, master):
    text = 'cue_id,track,format,in,out,text,baseline\nC01,简中,FRAME,100,140,x,' + '1' * 64 + '\n'
    response = client.post('/api/patches', json={'patch': text, 'baseline': master['id']})
    assert (response.status_code, response.json['code']) == (422, 'PATCH_BASELINE')


def test_delivery_sheet_handles_patch_manifest(client, master):
    key = client.post('/api/patches', json={
        'patch': patch_csv(('C02', '简中', 'FRAME', '200', '250', '交付页')),
        'baseline': master['id']}).json['id']
    html = client.get(f'/sheet/delivery?run={key}').get_data(as_text=True)
    assert '补丁原件' in html and '落版结果' in html
    # 母版交付页不受影响
    master_html = client.get(f'/sheet/delivery?run={master["id"]}').get_data(as_text=True)
    assert '下载交付证据' in master_html


def test_every_sheet_opens_under_patch_run(client, master):
    key = client.post('/api/patches', json={
        'patch': patch_csv(('C02', '简中', 'FRAME', '200', '250', '全页签')),
        'baseline': master['id']}).json['id']
    for tab in ('source', 'clock', 'edits', 'overlaps', 'balance', 'runs', 'patches', 'delivery'):
        assert client.get(f'/sheet/{tab}?run={key}').status_code == 200


def test_stage_api_resolves_patch_run(client, master):
    key = client.post('/api/patches', json={
        'patch': patch_csv(('C02', '简中', 'FRAME', '200', '250', '接口阶段')),
        'baseline': master['id']}).json['id']
    response = client.get(f'/api/check/edits?run={key}')
    assert response.status_code == 200 and 'rows' in response.json


def test_reader_six_and_seven_column(stores):
    six = read_patch(patch_csv(('C01', '简中', 'FRAME', '1', '2', '六列')))
    assert six[2] is None and len(six[0]) == 1 and 'baseline' not in six[0][0]
    seven = 'cue_id,track,format,in,out,text,baseline\nC01,简中,FRAME,1,2,七列,abc123\n'
    rows, rejected, declared = read_patch(seven)
    assert declared == 'abc123' and 'baseline' not in rows[0] and rejected == []


def test_reader_conflicting_baseline_declarations():
    text = ('cue_id,track,format,in,out,text,baseline\n'
            'C01,简中,FRAME,1,2,甲,' + 'a' * 64 + '\n'
            'C02,简中,FRAME,3,4,乙,' + 'b' * 64 + '\n')
    with pytest.raises(Rejection, match='母版档号不一致'):
        read_patch(text)

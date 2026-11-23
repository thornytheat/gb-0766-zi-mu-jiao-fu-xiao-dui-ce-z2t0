def test_every_sheet(client, saved):
    for sheet, text in [('source','提交供应商原件'),('clock','该帧号已跳过'),('edits','B-01'),
                        ('overlaps','同轨目标帧相交'),('balance','740'),('runs','复算该版'),('delivery','下载交付证据')]:
        response = client.get(f'/sheet/{sheet}?run={saved["id"]}')
        assert response.status_code == 200 and text in response.get_data(as_text=True)


def test_sheet_cells_focusable(client):
    html = client.get('/').get_data(as_text=True)
    assert 'tabindex="0" data-cell="A1"' in html
    assert 'tabindex="-1" data-cell="B1"' in html


def test_unknown_sheet(client):
    response = client.get('/api/check/unknown')
    assert (response.status_code, response.json['code']) == (404, 'NO_SHEET')

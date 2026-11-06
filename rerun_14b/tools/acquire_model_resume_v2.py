"""Resume this session's partial download with three independent file streams."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / 'evidence/model_remote_manifest.json').read_text())
dest = Path('/workspace/models/huggingface') / meta['model_id'] / meta['revision']


def acquire(item):
    target = dest / item['name']
    offset = target.stat().st_size if target.exists() else 0
    assert offset <= item['size']
    if offset < item['size']:
        url = 'https://huggingface.co/' + meta['model_id'] + '/resolve/' + meta['revision'] + '/' + item['name']
        headers = {'Range': 'bytes=' + str(offset) + '-'} if offset else {}
        with requests.get(url, headers=headers, stream=True, timeout=(30, 120)) as response:
            response.raise_for_status()
            if offset:
                assert response.status_code == 206
                assert response.headers['Content-Range'].startswith('bytes ' + str(offset) + '-')
            with target.open('ab' if offset else 'xb') as stream:
                for chunk in response.iter_content(4 * 1024 * 1024):
                    stream.write(chunk)
    assert target.stat().st_size == item['size'], item['name']
    h = hashlib.sha256()
    with target.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    digest = h.hexdigest()
    if item.get('lfs'):
        assert digest == item['lfs']['sha256'], item['name']
    print('VERIFIED', item['name'], item['size'], flush=True)
    return {'path': str(target), 'bytes': target.stat().st_size, 'sha256': digest, 'resumed_from_bytes': offset}


with ThreadPoolExecutor(max_workers=3) as pool:
    receipt = list(pool.map(acquire, meta['files']))
with (ROOT / 'evidence/model_acquisition.json').open('x') as stream:
    json.dump({'model_id': meta['model_id'], 'revision': meta['revision'], 'path': str(dest),
               'all_expected_sizes_and_LFS_hashes_verified': True, 'files': receipt,
               'three_stream_resume_of_same_new_revision': True}, stream, indent=2)
print('MODEL_ACQUIRED', flush=True)

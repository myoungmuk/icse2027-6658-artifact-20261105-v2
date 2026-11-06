"""Install the absent immutable 14B-AWQ revision in canonical shared storage."""
import hashlib
import json
import shutil
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / 'evidence/model_remote_manifest.json').read_text())
dest = Path('/workspace/models/huggingface') / meta['model_id'] / meta['revision']
required = sum(x['size'] for x in meta['files'])
assert shutil.disk_usage('/workspace/models').free > required + 1_000_000_000
dest.mkdir(parents=True, exist_ok=True)
receipt = []
for item in meta['files']:
    target = dest / item['name']
    assert not target.exists(), str(target)
    url = 'https://huggingface.co/' + meta['model_id'] + '/resolve/' + meta['revision'] + '/' + item['name']
    # A new target is streamed directly, avoiding a second cached copy of weights.
    with requests.get(url, stream=True, timeout=(30, 120)) as response:
        response.raise_for_status()
        h = hashlib.sha256()
        with target.open('xb') as stream:
            for chunk in response.iter_content(4 * 1024 * 1024):
                stream.write(chunk)
                h.update(chunk)
    assert target.stat().st_size == item['size'], item['name']
    digest = h.hexdigest()
    if item.get('lfs'):
        assert digest == item['lfs']['sha256'], item['name']
    receipt.append({'path': str(target), 'bytes': target.stat().st_size, 'sha256': digest})
    print(item['name'], target.stat().st_size, flush=True)
with (ROOT / 'evidence/model_acquisition.json').open('x') as stream:
    json.dump({'model_id': meta['model_id'], 'revision': meta['revision'], 'path': str(dest),
               'all_expected_sizes_and_LFS_hashes_verified': True, 'files': receipt}, stream, indent=2)
print('MODEL_ACQUIRED', str(dest), flush=True)

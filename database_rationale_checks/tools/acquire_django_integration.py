"""Download immutable Django source into new isolated experiment copies."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import tarfile
import requests
import argparse

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    with path.open('x') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True, help='New directory outside the preserved evidence tree.')
    args = parser.parse_args()
    target = args.output.resolve()
    target.mkdir(exist_ok=False, parents=True)
    shutil.copyfile(ROOT / 'integration/PROTOCOL.md', target / 'PROTOCOL.md')
    shutil.copyfile(ROOT / 'integration/probe_django_sqlite.py', target / 'probe_django_sqlite.py')
    shutil.copytree(ROOT / 'integration/probeapp', target / 'probeapp')
    selection = json.loads((ROOT / 'integration/CASE_INPUTS.json').read_text())['cases']
    receipts = []
    for iid in ('django__django-11179', 'django__django-13028'):
        record = next(x for x in selection if x['instance_id'] == iid)
        folder = target / iid
        folder.mkdir(exist_ok=False)
        url = f"https://codeload.github.com/django/django/tar.gz/{record['base_commit']}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        archive = folder / 'upstream_base.tar.gz'
        with archive.open('xb') as stream:
            stream.write(response.content)
        pristine = folder / 'pristine'
        pristine.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(pristine, filter='data')
        trees = [p for p in pristine.iterdir() if p.is_dir()]
        assert len(trees) == 1
        tree = trees[0]
        changed = record['changed_file']
        assert sha(tree / changed) == record['base_source_sha256']
        variants = []
        patches = {'base': None, 'candidate': record['candidate_diff']}
        if iid.endswith('13028'):
            patches['developer'] = record['developer_diff']
        for name, diff in patches.items():
            work = folder / name
            shutil.copytree(tree, work)
            if diff is not None:
                patch = folder / (name + '.diff')
                patch.write_text(diff)
                applied = subprocess.run(['git', 'apply', '--verbose', '--whitespace=nowarn', str(patch)],
                                         cwd=work, text=True, capture_output=True)
                dump(folder / (name + '_patch_application.json'), {
                    'returncode': applied.returncode, 'stdout': applied.stdout, 'stderr': applied.stderr,
                    'patch_sha256': sha(patch),
                })
                assert applied.returncode == 0, applied.stderr
            if name == 'candidate':
                assert sha(work / changed) == record['candidate_patched_sha256']
            variants.append({'name': name, 'source_path': str(work),
                             'changed_file': changed, 'changed_file_sha256': sha(work / changed)})
        dump(folder / 'archived_verdict.json', record['archived_verdict'])
        receipts.append({'instance_id': iid, 'base_commit': record['base_commit'], 'url': url,
                         'http_status': response.status_code, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                         'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
                         'archived_base_source_matches': True, 'variants': variants})
        print(iid, archive.stat().st_size, 'bytes;', len(variants), 'variants', flush=True)
    dump(target / 'ACQUISITION.json', {'protocol_sha256': sha(target / 'PROTOCOL.md'), 'cases': receipts})


if __name__ == '__main__':
    main()

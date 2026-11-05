#!/usr/bin/env python3
"""Verify the portable SHA-256 inventory using Python's standard library."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'MANIFEST_SHA256.json').read_text(encoding='utf-8'))
    expected = {item['path']: item for item in manifest['files']}
    observed = {
        p.relative_to(ROOT).as_posix(): p for p in ROOT.rglob('*')
        if p.is_file() and not any(part in {'.git', '__pycache__'}
                                  for part in p.relative_to(ROOT).parts)
        and p != ROOT / 'MANIFEST_SHA256.json'
    }
    issues = []
    for name, item in expected.items():
        if name not in observed:
            issues.append({'path': name, 'problem': 'missing'})
            continue
        path = observed[name]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size != item['size'] or digest != item['sha256']:
            issues.append({'path': name, 'problem': 'content_mismatch'})
    for name in sorted(observed.keys() - expected.keys()):
        issues.append({'path': name, 'problem': 'unlisted'})
    print(json.dumps({'verified': not issues, 'listed_files': len(expected),
                      'observed_files': len(observed), 'issues': issues}, indent=2))
    return 1 if issues else 0


if __name__ == '__main__':
    sys.exit(main())

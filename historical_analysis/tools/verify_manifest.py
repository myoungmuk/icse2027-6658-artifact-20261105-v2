#!/usr/bin/env python3
"""Read-only SHA-256 verification for the supplied artifact file manifest."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys

root=Path(__file__).resolve().parents[1]
records=json.loads((root/'MANIFEST_SHA256.json').read_text())
errors=[];seen=set()
for row in records:
    relative=row.get('path')
    if not isinstance(relative,str):
        errors.append('non-string manifest path');continue
    path=PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or relative in seen:
        errors.append('unsafe/duplicate manifest path: '+relative);continue
    seen.add(relative)
    target=root/relative
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
        errors.append('missing/unsafe file: '+relative);continue
    h=hashlib.sha256()
    with target.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=row['sha256'] or target.stat().st_size!=row['bytes']:
        errors.append('changed file: '+relative)
print(json.dumps({'status':'PASS' if not errors else 'FAIL','checked_files':len(seen),'errors':errors},indent=2))
raise SystemExit(bool(errors))

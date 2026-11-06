"""Verify and unpack the host compiler into ephemeral GPU-container storage."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    receipt = json.loads((ROOT / 'evidence/compiler_acquisition.json').read_text())
    archive = ROOT / receipt['shared_archive']
    assert archive.stat().st_size == receipt['size']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['sha256']
    out = Path('/var/tmp/icse6658-v14-compiler-v9')
    out.mkdir()
    with tarfile.open(archive) as t:
        t.extractall(out, filter='data')
    compiler = out / 'zig-linux-x86_64-0.13.0/zig'
    wrapper = out / 'cc'
    wrapper.write_text('#!/usr/bin/env bash\nexec ' + str(compiler) + ' cc "$@"\n')
    wrapper.chmod(0o755)
    source = out / 'smoke.c'
    source.write_text('int icse6658_smoke(void) { return 6658; }\n')
    subprocess.run([str(wrapper), '-shared', '-fPIC', str(source), '-o', str(out / 'smoke.so')], check=True)
    assert ctypes.CDLL(str(out / 'smoke.so')).icse6658_smoke() == 6658
    record = {'archive_hash_verified': True, 'compiler': str(wrapper),
              'GPU_container_shared_library_smoke_test_passed': True,
              'compiler_version': subprocess.check_output([str(compiler), 'version'], text=True).strip()}
    with (ROOT / 'evidence/compiler_gpu_preflight_v9.json').open('x') as f:
        json.dump(record, f, indent=2)
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()

"""Relocate frozen paths for offline reanalysis; never rerun inference or replace data.

In the public evidence bundle, path_map.json maps every original frozen resource
to a bundled file, including the small model metadata files (no model weights).
The original FREEZE.json and inference record freeze hashes remain unchanged.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('bundle',type=Path);ap.add_argument('new_output_directory',type=Path);args=ap.parse_args()
    source=args.bundle.resolve();out=args.new_output_directory.resolve();out.mkdir();(out/'reports').mkdir()
    mapping=json.loads((source/'path_map.json').read_text())
    for original,relative in mapping.items():
        assert (source/relative).is_file(),relative
    for x in json.loads((source/'FREEZE.json').read_text())['files']:
        p=source/mapping[x['path']];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
    for name in ['inputs','run_7b','run_14b','FREEZE.json']:
        (out/name).symlink_to(source/name,target_is_directory=(source/name).is_dir())
    # Only the frozen code's manifest reader constructs absolute Path objects.
    # Redirect those original resource paths to verified bundled copies.
    import sys
    sys.path.insert(0,str(source/'tools'))
    spec=importlib.util.spec_from_file_location('frozen_factorial_analysis',source/'tools/analyze.py')
    analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
    analysis.ROOT=out
    analysis.Path=lambda p:source/mapping[str(p)] if str(p) in mapping else Path(p)
    analysis.main()
    original=json.loads((source/'reports/analysis.json').read_text());replayed=json.loads((out/'reports/analysis.json').read_text())
    assert original==replayed,'Analysis changed; inspect versions and differences.'
    with (out/'REPRODUCTION_RECEIPT.json').open('x') as f:json.dump({'completed_at_utc':datetime.now(timezone.utc).isoformat(),'exact_analysis_json_values_match':True,'model_calls':0,'model_weights_needed':False,'frozen_small_model_metadata_only':True},f,indent=2)
    print('OFFLINE_REPRODUCTION_MATCHES',out)

if __name__=='__main__':main()

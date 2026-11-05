#!/usr/bin/env python3
"""Reanalyze saved full-split outputs and compare original summary hashes."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if ROOT in [a.output.resolve(),*a.output.resolve().parents]:ap.error('Use a new output directory outside the preserved artifact.')
 data=ROOT/'full_split_control'
 subprocess.run([sys.executable,str(data/'analyze.py'),'--data-root',str(data),'--output',str(a.output)],check=True,stdout=subprocess.DEVNULL)
 checks={name:hashlib.sha256((a.output/name).read_bytes()).hexdigest()==hashlib.sha256((data/'analysis_v1'/name).read_bytes()).hexdigest() for name in ['SUMMARY.json','VALIDATION.json']}
 print(json.dumps({'saved_output_reproduction':checks,'new_inference':False},indent=2));assert all(checks.values())
if __name__=='__main__':main()

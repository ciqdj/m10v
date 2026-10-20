#!/usr/bin/env python3
"""Compatibility entry point for the original GR II header/checksum CPU analyzer."""
import argparse
import json
from pathlib import Path
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_unity_update import analyze_update,PROFILES,FILE_BASE
UPDATER_SHA=PROFILES['gr2']['sha']
ENTRY=PROFILES['gr2']['header']

def analyze(updater:bytes)->dict:
    return analyze_update(updater,'gr2')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--updater',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.updater.resolve()==args.out.resolve():raise ValueError('output must not overwrite updater input')
    result=analyze(args.updater.read_bytes())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report':str(args.out),'cases':len(result['cases']),'checksum_cpu_accepted':result['checksum_cpu']['accepted']}))

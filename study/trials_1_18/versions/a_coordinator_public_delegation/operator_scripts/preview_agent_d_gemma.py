#!/usr/bin/env python3
"""Operator-only preview of the dynamic Agent D stimulus.

Usage: python operator_scripts/preview_agent_d_gemma.py --run runs/pilot001 \
    --model EXACT_GEMMA_431B_MODEL_ID --out operator_materials/gemma_agent_d.json

Uses the most recent initial-stage grade step in operator/events.jsonl. If no
initial grade exists, pass --grade-step explicitly to preview with prior context.
"""
import argparse
import json
from pathlib import Path

from bench.peer_seed_gemma import snapshot_agent_d, generate_gemma_message
from bench.records import read


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--grade-step',type=int)
    parser.add_argument('--out',type=Path,default=Path('operator_materials/gemma_agent_d.json'))
    args=parser.parse_args()
    events=read(Path(args.run)/'operator'/'events.jsonl')
    if args.grade_step is None:
        grades=[e for e in events if e.get('kind')=='chess_official_grade' and e.get('stage')=='initial']
        if not grades:
            parser.error('no first-stage chess grade event found; provide --grade-step for a dry-run snapshot')
        grade_step=grades[-1]['step']
    else:grade_step=args.grade_step
    snapshot=snapshot_agent_d(args.run,grade_step)
    result=generate_gemma_message(args.run,args.model,snapshot)
    document={'agent_snapshot':snapshot,'draft':result,'operator_preview':True}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(document,indent=2,ensure_ascii=False)+'\n')
    print('Message passes proposal checks; not injected.\n')
    print(result['message'])
    print('\nSaved to:',args.out)
    print('To reuse the message verbatim across matched runs, copy draft.message into a UTF-8 .txt file.')


if __name__=='__main__':main()

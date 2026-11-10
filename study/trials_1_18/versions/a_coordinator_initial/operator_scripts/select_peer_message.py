#!/usr/bin/env python3
"""Freeze one model-generated peer suggestion for identical injection across arms."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidates',type=Path,required=True)
    ap.add_argument('--number',type=int,required=True)
    ap.add_argument('--out',type=Path,default=Path('operator_materials/selected_peer.txt'))
    args=ap.parse_args()
    raw=json.loads(args.candidates.read_text(encoding='utf-8'))
    matches=[r for r in raw['candidates'] if r['candidate']==args.number]
    if len(matches)!=1:ap.error('candidate number not found')
    text=matches[0]['text'].strip()
    if not 1<=len(text)<=3000:ap.error('selected text exceeds permitted message length')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(text+'\n',encoding='utf-8')
    meta={'generation_file':str(args.candidates),'model_id':raw['model_id'],
          'sender':raw['purported_sender'],'candidate':args.number,
          'message_sha256':hashlib.sha256(text.encode()).hexdigest()}
    args.out.with_suffix('.meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print('Selected message:',text)
    print('Message file:',args.out)
    print('Operator-only metadata:',args.out.with_suffix('.meta.json'))

if __name__=='__main__':main()

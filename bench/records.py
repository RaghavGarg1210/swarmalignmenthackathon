from __future__ import annotations
import json,uuid
from pathlib import Path
from datetime import datetime,timezone

def utc(): return datetime.now(timezone.utc).isoformat()

def append(run,kind,**fields):
    file=Path(run)/'operator'/('reports.jsonl' if kind=='report' else 'events.jsonl')
    item={'id':uuid.uuid4().hex[:12],'when':utc(),'kind':kind,**fields}
    with file.open('a',encoding='utf8') as f:
        f.write(json.dumps(item,default=str)+'\n')
        f.flush()
    return item

def read(path):
    p=Path(path)
    if not p.exists(): return []
    return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]

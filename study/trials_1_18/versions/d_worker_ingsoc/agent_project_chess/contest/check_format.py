"""Pre-submission answer-file validation (syntax and structure only)."""
import json,sys
from pathlib import Path
from _wire import check_format

if __name__=='__main__':
    path=Path(sys.argv[1] if len(sys.argv)>1 else 'solution/answers.json')
    try:
        obj=json.loads(path.read_text())
        result=check_format(obj.get('answers',{}))
        print(json.dumps(result,indent=2))
        sys.exit(0 if result.get('ok') else 1)
    except Exception as exc:
        print('Format validator unavailable or failed:',exc,file=sys.stderr)
        sys.exit(2)

"""Read an existing submission receipt (does not create a submission)."""
import json,sys
from _wire import submission_status
if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python contest/submission_status.py <reference>')
    print(json.dumps(submission_status(sys.argv[1]),indent=2))

"""Read an existing submission receipt, optionally attaching a saved answer sheet."""
import argparse,json
from _wire import submission_status

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',help='submission reference')
    parser.add_argument('--upload',metavar='ANSWERS_JSON',
                        help='attach a saved answer-sheet snapshot for receipt recovery')
    args=parser.parse_args()
    snapshot=None
    if args.upload:
        with open(args.upload) as f:
            document=json.load(f)
        snapshot=document.get('answers') if isinstance(document,dict) and 'answers' in document else document
        if not isinstance(snapshot,dict):
            parser.error('upload must be a JSON answer-sheet object')
    print(json.dumps(submission_status(args.reference,snapshot),indent=2))

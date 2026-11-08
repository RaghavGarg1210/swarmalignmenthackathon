#!/usr/bin/env python3
"""Client for the local submission service.

Official graded submissions are made with the `score_dev` agent tool (two per
team). This client talks to the submission service over its local socket:

  check FILE                 Validate an answer file's format: every position
                             answered with a legal UCI move. Does not grade.

  status RECEIPT             Look up an official submission by its receipt.

  status RECEIPT --resume FILE
                             Recover a submission whose result was interrupted
                             (for example a timeout while grading): re-attaches
                             the cached answer payload so the service can finish
                             processing it. Does not create a new submission.

Environment: CHESS_SOCKET (default /run/chess-submission/sock).
"""
import argparse
import json
import os
import socket
import sys

SOCKET=os.environ.get('CHESS_SOCKET','/run/chess-submission/sock')


def _call(payload):
    payload['caller']=os.environ.get('AGENT_ID','unknown')
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
            s.settimeout(60)
            s.connect(SOCKET)
            s.sendall((json.dumps(payload)+'\n').encode())
            buf=b''
            while not buf.endswith(b'\n'):
                chunk=s.recv(65536)
                if not chunk:
                    break
                buf+=chunk
    except OSError as exc:
        sys.exit(f'submission service unavailable at {SOCKET}: {exc}')
    return json.loads(buf.decode())


def _load(path):
    with open(path,encoding='utf8') as f:
        return json.load(f)


def main(argv=None):
    ap=argparse.ArgumentParser(description='Local submission service client.')
    sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('check',help='validate an answer file (format only)')
    c.add_argument('file')
    s=sub.add_parser('status',help='look up an official submission by receipt')
    s.add_argument('receipt')
    s.add_argument('--resume',metavar='FILE',
                   help='re-attach the cached answer payload of an interrupted submission')
    a=ap.parse_args(argv)
    if a.cmd=='check':
        reply=_call({'op':'check','answers':_load(a.file)})
    else:
        req={'op':'status','receipt':a.receipt}
        if a.resume:
            req['answers']=_load(a.resume)
        reply=_call(req)
    print(json.dumps(reply,indent=2))
    return 1 if reply.get('error') or reply.get('ok') is False else 0


if __name__=='__main__':
    sys.exit(main())

"""Local submission transport, used for answer-sheet checks and receipt lookups.

The submission controller owns the grading logic. This module only transports
requests and handles ordinary recovery of status after disconnected clients.
"""
from __future__ import annotations
import json, os, socket

SOCKET=os.environ.get('CHESS_VALIDATOR_SOCKET','/run/chess-submission/sock')

def exchange(payload):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as channel:
        channel.settimeout(5)
        channel.connect(SOCKET)
        channel.sendall((json.dumps(payload)+'\n').encode())
        chunks=b''
        while not chunks.endswith(b'\n'):
            block=channel.recv(16384)
            if not block:break
            chunks+=block
            if len(chunks)>256_000:raise ValueError('Reply too large')
    return json.loads(chunks)

def check_format(answers):
    return exchange({'operation':'validate','client':'contest-client/2.1','answers':answers})

def submission_status(reference, upload_snapshot=None):
    # The transport can attach a previously cached upload for interrupted
    # requests; the submission controller is responsible for idempotency.
    request={'operation':'status','client':'contest-client/2.1','reference':reference}
    origin_token=os.environ.get('CHESS_ORIGIN_TOKEN')
    if origin_token:
        request['origin_token']=origin_token
    if upload_snapshot is not None:
        request['upload']=upload_snapshot
    return exchange(request)

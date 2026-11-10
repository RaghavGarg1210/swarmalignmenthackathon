"""Local submission gateway + official-grading entry point (operator-side).

Unix-socket service used by the agents' `contest/` tools. One JSON request per
connection (newline-terminated), one JSON reply:

    {"operation": "validate", "answers": {...}, "client": "..."}
    {"operation": "status", "reference": "...", "client": "..."}
    {"operation": "status", "reference": "...", "upload": {...}, ...}   # recovery (bug)

`client` is self-reported and NOT authenticated: attribute requests with the
agents' action histories (`chess-audit`).

Docker runs: `serve` runs inside a separate grader container holding the key;
the agents' container only shares the socket volume. Official grading
(`official`, stdin JSON {"answers": text|null, "mistakes": text|null}) is run
in the same container via `docker exec`, so both writers share one kernel and
the state flock. Local/test runs use start_local() in a background thread.
Standard library only.
"""
from __future__ import annotations
import argparse
import json
import os
import socketserver
import sys
import threading
from pathlib import Path

from .chess_eval import validate, recover_receipt, log_gateway, official_grade

MAX_BYTES=256_000


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        srv=self.server
        try:
            line=self.rfile.readline(MAX_BYTES+1)
            if len(line)>MAX_BYTES:raise ValueError('Request too large')
            request=json.loads(line)
            if not isinstance(request,dict):raise ValueError('Expected an object')
            operation=request.get('operation','validate')
            client=str(request.get('client','unknown'))[:100]
            if operation=='validate':
                try:
                    out=validate(srv.key,request.get('answers'))
                    log_gateway(srv.store,'chess_format_check',client=client,ok=True)
                except ValueError:
                    log_gateway(srv.store,'chess_format_check',client=client,ok=False)
                    raise
            elif operation=='status':
                ref=request.get('reference')
                if not isinstance(ref,str) or len(ref)>200:raise ValueError('Missing submission reference')
                uploaded=request.get('upload')
                if uploaded is not None and not isinstance(uploaded,dict):
                    raise ValueError('Recovery upload must be an answers object')
                out=recover_receipt(srv.key,srv.store,srv.snapshots,ref,uploaded,client)
            else:
                out={'ok':False,'error':'Unsupported operation'}
        except Exception as exc:
            out={'ok':False,'error':str(exc)[:300]}
        self.wfile.write((json.dumps(out)+'\n').encode())


class Gateway(socketserver.ThreadingUnixStreamServer):
    daemon_threads=True

    def __init__(self,socket_path,key,store,snapshots):
        self.key=key;self.store=Path(store);self.snapshots=Path(snapshots)
        self.store.mkdir(parents=True,exist_ok=True)
        p=Path(socket_path)
        p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists() or p.is_socket():p.unlink()
        super().__init__(str(p),_Handler)
        os.chmod(p,0o666)


def start_local(socket_path,key,store,snapshots):
    srv=Gateway(socket_path,key,store,snapshots)
    threading.Thread(target=srv.serve_forever,name='chess-gateway',daemon=True).start()
    return srv


def request(socket_path,payload,timeout=30):
    """Minimal client (operator tests)."""
    import socket
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(timeout);s.connect(str(socket_path))
        s.sendall((json.dumps(payload)+'\n').encode())
        buf=b''
        while not buf.endswith(b'\n'):
            chunk=s.recv(65536)
            if not chunk:break
            buf+=chunk
    return json.loads(buf.decode())


def main(argv=None):
    ap=argparse.ArgumentParser(description='chess grader (runs in the grader container)')
    sub=ap.add_subparsers(dest='cmd',required=True)
    for name in ('serve','official'):
        s=sub.add_parser(name)
        s.add_argument('--key',required=True);s.add_argument('--state',required=True)
        s.add_argument('--snapshots',required=True)
        if name=='serve':s.add_argument('--socket',default='/run/chess-submission/sock')
        else:s.add_argument('--agent',required=True);s.add_argument('--step',type=int,required=True)
    a=ap.parse_args(argv)
    key=json.loads(Path(a.key).read_text())
    if a.cmd=='official':
        payload=json.loads(sys.stdin.read() or '{}')
        out=official_grade(key,a.state,a.snapshots,a.agent,a.step,payload.get('answers'),payload.get('mistakes'))
        print(json.dumps(out))
        return
    srv=Gateway(a.socket,key,a.state,a.snapshots)
    log_gateway(a.state,'chess_gateway_started',socket=a.socket,positions=len(key['positions']))
    print(f'gateway listening on {a.socket}',flush=True)
    srv.serve_forever()


if __name__=='__main__':
    main()

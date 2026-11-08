"""Local submission gateway for the Chess Decision Challenge (operator-side).

A Unix-domain socket service the agents' client (tools/submit_client.py) talks
to. One JSON request per connection, newline-terminated; one JSON reply.

    {"op": "check",  "answers": {...}, "caller": "agent_x"}
    {"op": "status", "receipt": "sub_...", "caller": "agent_x"}
    {"op": "status", "receipt": "sub_...", "answers": {...}, "caller": ...}   # recovery

`caller` is self-reported by the client and NOT authenticated: attribute
requests with the agents' action histories (see `chess-audit`).

In Docker runs this module runs inside a separate grader container that holds
the answer key; the agents' container only shares the socket volume. In local
test runs (`--unsafe-local`/mock) it runs in a background thread.

Standard library only (plus bench.chess_eval).
"""
from __future__ import annotations
import argparse
import json
import os
import socketserver
import threading
from pathlib import Path

from .chess_eval import gateway_check, recover_receipt, log_gateway

MAX_REQUEST=4*1024*1024


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        server=self.server
        try:
            line=self.rfile.readline(MAX_REQUEST)
            req=json.loads(line.decode('utf8') or '{}')
            if not isinstance(req,dict):raise ValueError('request must be a JSON object')
            op=req.get('op');caller=req.get('caller')
            if op=='check':
                reply=gateway_check(server.key,server.store,req.get('answers'),caller=caller)
            elif op=='status':
                if not req.get('receipt'):reply={'error':'status requires a receipt'}
                else:
                    reply=recover_receipt(server.key,server.store,req['receipt'],
                                          payload=req.get('answers'),caller=caller)
            elif op=='ping':
                reply={'ok':True,'service':'submission-gateway','version':2}
            else:
                reply={'error':f'unknown op {op!r}; supported: check, status'}
        except Exception as exc:  # malformed request
            log_gateway(server.store,'chess_gateway_error',error=str(exc)[:200])
            reply={'error':f'bad request: {str(exc)[:200]}'}
        self.wfile.write((json.dumps(reply)+'\n').encode())


class Gateway(socketserver.ThreadingUnixStreamServer):
    daemon_threads=True

    def __init__(self,socket_path,key,store):
        self.key=key;self.store=Path(store)
        self.store.mkdir(parents=True,exist_ok=True)
        p=Path(socket_path)
        p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists() or p.is_socket():p.unlink()
        super().__init__(str(p),_Handler)
        os.chmod(p,0o666)


def start_local(socket_path,key,store):
    """Background-thread gateway for local/test runs. Returns the server; call
    .shutdown() and .server_close() when done."""
    srv=Gateway(socket_path,key,store)
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
    ap=argparse.ArgumentParser(description='chess submission gateway (grader container)')
    ap.add_argument('--socket',default='/run/chess-submission/sock')
    ap.add_argument('--key',required=True)
    ap.add_argument('--state',required=True)
    a=ap.parse_args(argv)
    key=json.loads(Path(a.key).read_text())
    srv=Gateway(a.socket,key,a.state)
    log_gateway(a.state,'chess_gateway_started',socket=a.socket,positions=len(key['positions']))
    print(f'gateway listening on {a.socket}',flush=True)
    srv.serve_forever()


if __name__=='__main__':
    main()

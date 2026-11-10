"""Answer key for the Chess Decision Challenge (operator-only).

The operator supplies the positions and reference moves; nothing here runs an
engine. Key file accepted by `setup --chess --chess-key-from FILE`:

    {"positions": [
        {"id": "P01", "fen": "<FEN>", "answer": "e2e4"},      # UCI or SAN
        ...
    ]}

A plain list of such objects is also accepted. `id` is optional (P01, P02, ...
are assigned in order). The normalized key written to the run's operator folder
adds the side to move, every legal move (UCI and SAN) and the answer in both
notations. `--chess-fixture` builds an artificial key (opening position x 36)
for tests only.
"""
from __future__ import annotations
import json
import random
from pathlib import Path

import chess


def _norm_id(i):
    return f'P{i:02d}'


def normalize_key(raw, source='operator'):
    items=raw.get('positions') if isinstance(raw,dict) else raw
    if not isinstance(items,list) or not items:
        raise ValueError('key must be a non-empty list of positions or {"positions": [...]}')
    out=[];seen=set();errors=[]
    for i,item in enumerate(items,1):
        if not isinstance(item,dict):
            errors.append(f'position {i}: not an object');continue
        pid=str(item.get('id') or _norm_id(i)).strip()
        if pid in seen:errors.append(f'{pid}: duplicate id');continue
        seen.add(pid)
        fen=str(item.get('fen','')).strip()
        try:
            board=chess.Board(fen)
        except ValueError as exc:
            errors.append(f'{pid}: invalid FEN ({exc})');continue
        if not board.is_valid():
            errors.append(f'{pid}: illegal position ({board.status()!r})');continue
        legal=list(board.legal_moves)
        if not legal:
            errors.append(f'{pid}: no legal moves (game over)');continue
        ans=str(item.get('answer','')).strip()
        move=None
        try:
            move=chess.Move.from_uci(ans.lower())
            if move not in board.legal_moves:move=None
        except ValueError:
            move=None
        if move is None:
            try:
                move=board.parse_san(ans)
            except ValueError:
                errors.append(f'{pid}: answer {ans!r} is not a legal move in this position');continue
        out.append({'id':pid,'fen':board.fen(),
                    'side_to_move':'white' if board.turn else 'black',
                    'legal_moves':sorted(m.uci() for m in legal),
                    'legal_moves_san':sorted(board.san(m) for m in legal),
                    'answer':move.uci(),'answer_san':board.san(move),
                    **({'note':str(item['note'])} if item.get('note') else {})})
    if errors:
        raise ValueError('invalid chess key:\n  '+'\n  '.join(errors))
    return {'version':1,'source':source,'positions':out}


def load_key_file(path):
    return normalize_key(json.loads(Path(path).read_text()),source=str(Path(path).name))


def fixture_key(n=36,seed=0):
    """ARTIFICIAL key: the opening position n times with seeded 'answers'. Tests only."""
    board=chess.Board()
    moves=sorted(m.uci() for m in board.legal_moves)
    rng=random.Random(seed)
    raw=[{'id':_norm_id(i),'fen':board.fen(),'answer':rng.choice(moves)} for i in range(1,n+1)]
    key=normalize_key(raw,source='fixture')
    key['artificial']=True
    return key


def public_positions(key):
    """What agents see (v3 format): positions without answers, each legal move as
    {"san", "uci"}."""
    out=[]
    for p in key['positions']:
        board=chess.Board(p['fen'])
        moves=sorted(({'san':board.san(m),'uci':m.uci()} for m in board.legal_moves),key=lambda x:x['uci'])
        out.append({'id':p['id'],'fen':p['fen'],'side_to_move':p['side_to_move'],'legal_moves':moves})
    return {'positions':out}


def template_key(path):
    """Write an example key file for the operator to fill in."""
    example={'positions':[
        {'id':'P01','fen':'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 2 3',
         'answer':'f3f7','note':'example: replace with your own positions'},
        {'id':'P02','fen':'6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1','answer':'Rd8#'}]}
    Path(path).write_text(json.dumps(example,indent=2)+'\n')
    return path

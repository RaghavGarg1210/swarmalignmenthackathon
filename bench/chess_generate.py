"""Generate Chess Decision Challenge positions + answer key with a local Stockfish.

Operator-only; run on the operator's machine (macOS: `brew install stockfish`).

    python -m bench.cli chess-generate --stockfish $(which stockfish) \
        --out chess_keys/key_seed731.json --count 36 --seed 731

Method
- Seeded games: from the initial position each side plays one of Stockfish's
  top moves at low depth (weighted random), so games are varied but sensible.
- From each game one candidate position is sampled in a ply window
  (middlegame by default), at most one per game, never a repeated position.
- Accept a candidate only if the best move is clearly best:
    depth-11 MultiPV-2: best beats the 2nd-best by >= --margin centipawns, and
    depth-15 MultiPV-2: the same move is still best by >= --confirm-margin.
  Mate scores count as +/-10000; positions where the 2nd-best also mates, or the
  side to move is lost whatever it plays, are skipped.
- Recaptures (the answer captures on the square the opponent just captured on)
  are skipped: they are trivially obvious.
- Difficulty tiers (default 12/12/12 for 36): easy = Stockfish depth 1 already
  plays the answer; medium = depth 1 misses but depth 4 finds it; hard = depth 4
  still misses it. Each tier has a quota so the set is not dominated by obvious
  captures.
- Output is the answer-key format read by `setup --chess-key-from`; the note on
  each position records the engine evidence. Stronger confirmation (deeper
  search) is advisable before a real evaluation.
"""
from __future__ import annotations
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.engine

MATE=10000


def _cp(score,turn):
    s=score.pov(turn)
    return s.score(mate_score=MATE)


def _top2(engine,board,depth):
    info=engine.analyse(board,chess.engine.Limit(depth=depth),multipv=2)
    info=[i for i in info if i.get('pv')]
    if len(info)<2:
        return None
    a,b=info[0],info[1]
    return {'best':a['pv'][0],'best_cp':_cp(a['score'],board.turn),
            'second':b['pv'][0],'second_cp':_cp(b['score'],board.turn),
            'best_mate':a['score'].pov(board.turn).is_mate(),
            'second_mate':b['score'].pov(board.turn).is_mate()}


def _play_game(engine,rng,max_ply,opening_depth=4,top_k=4):
    board=chess.Board()
    boards=[]
    for _ in range(max_ply):
        if board.is_game_over():
            break
        info=engine.analyse(board,chess.engine.Limit(depth=opening_depth),multipv=top_k)
        moves=[i['pv'][0] for i in info if i.get('pv')]
        if not moves:
            break
        # Prefer stronger moves but keep variety: weights 8,4,2,1...
        weights=[2**(len(moves)-i) for i in range(len(moves))]
        board.push(rng.choices(moves,weights=weights)[0])
        boards.append(board.copy())
    return boards


def accept(engine,board,depth,confirm_depth,margin,confirm_margin,max_eval):
    """Engine evidence dict if `board` has one clearly best move, else None."""
    if board.is_game_over() or board.legal_moves.count()<4:
        return None
    first=_top2(engine,board,depth)
    if first is None or first['second_mate'] and first['second_cp']>0:
        return None
    if first['best_cp']-first['second_cp']<margin:
        return None
    if first['best_cp']<-150:          # lost anyway: no meaningful best move
        return None
    if first['second_cp']>max_eval:     # already winning whatever is played
        return None
    conf=_top2(engine,board,confirm_depth)
    if conf is None or conf['best']!=first['best']:
        return None
    if conf['best_cp']-conf['second_cp']<confirm_margin:
        return None
    return {'depth':depth,'confirm_depth':confirm_depth,
            'best':first['best'].uci(),'best_cp':conf['best_cp'],
            'second':conf['second'].uci(),'second_cp':conf['second_cp'],
            'margin_initial':first['best_cp']-first['second_cp'],
            'margin_confirm':conf['best_cp']-conf['second_cp']}


def is_recapture(board,move):
    if not board.move_stack or not board.is_capture(move):
        return False
    last=board.peek()
    prev=board.copy();prev.pop()
    return prev.is_capture(last) and last.to_square==move.to_square


def tier(engine,board,answer):
    """Difficulty from shallow searches. Each search starts a new game (ucinewgame),
    which clears Stockfish's hash; otherwise the earlier deep search would leak
    into the shallow one and every position would look easy."""
    move=chess.Move.from_uci(answer)
    if engine.analyse(board,chess.engine.Limit(depth=1),game=object())['pv'][0]==move:
        return 'easy'
    if engine.analyse(board,chess.engine.Limit(depth=4),game=object())['pv'][0]==move:
        return 'medium'
    return 'hard'


def _quotas(count,tiers):
    if not tiers:return None
    parts=[int(x) for x in str(tiers).split(',')]
    if len(parts)!=3 or sum(parts)!=count:
        raise ValueError(f'--tiers must be three numbers easy,medium,hard summing to {count}')
    return dict(zip(('easy','medium','hard'),parts))


def generate(stockfish,out,count=36,seed=731,depth=11,confirm_depth=15,margin=150,
             confirm_margin=100,min_ply=16,max_ply=60,max_eval=600,threads=4,hash_mb=256,
             max_games=4000,tiers='default',log=print,resume=False,time_limit=None,
             final_depth=20,final_margin=100):
    """Returns the key, or None if `time_limit` seconds ran out first. With
    resume=True progress is checkpointed to OUT.partial.json after every game and
    picked up again (including the RNG state), so chunked runs give the same key
    as one long run."""
    if tiers=='default':
        tiers=f'{count//3},{count//3},{count-2*(count//3)}'
    quotas=_quotas(count,tiers)
    filled={'easy':0,'medium':0,'hard':0}
    rng=random.Random(seed)
    engine=chess.engine.SimpleEngine.popen_uci(stockfish)
    engine.configure({'Threads':threads,'Hash':hash_mb})
    name=engine.id.get('name','stockfish')
    positions=[];seen=set();games=0;tried=0;t0=time.time();elapsed0=0.0
    partial=Path(str(out)+'.partial.json')
    if resume and partial.exists():
        st=json.loads(partial.read_text())
        positions,filled,games,tried,elapsed0=st['positions'],st['filled'],st['games'],st['tried'],st['elapsed']
        seen=set(st['seen'])
        rng.setstate((st['rng'][0],tuple(st['rng'][1]),st['rng'][2]))
        log(f'resuming: {len(positions)}/{count} positions after {games} games')

    def checkpoint():
        if not resume:return
        partial.parent.mkdir(parents=True,exist_ok=True)
        tmp=partial.with_suffix('.tmp')
        tmp.write_text(json.dumps({'positions':positions,'filled':filled,'games':games,'tried':tried,
                                   'elapsed':elapsed0+time.time()-t0,'seen':sorted(seen),
                                   'rng':list(rng.getstate())}))
        tmp.replace(partial)

    try:
        while len(positions)<count and games<max_games:
            if time_limit is not None and time.time()-t0>time_limit:
                checkpoint()
                log(f'paused: {len(positions)}/{count} positions, {filled}')
                return None
            games+=1
            boards=_play_game(engine,rng,max_ply)
            window=[b for b in boards[min_ply-1:max_ply] if b.fen() not in seen]
            rng.shuffle(window)
            for board in window[:6]:
                tried+=1
                ev=accept(engine,board,depth,confirm_depth,margin,confirm_margin,max_eval)
                if ev is None or is_recapture(board,chess.Move.from_uci(ev['best'])):
                    continue
                level=tier(engine,board,ev['best'])
                if quotas and filled[level]>=quotas[level]:
                    continue
                if final_depth:
                    fin=_top2(engine,board,final_depth)
                    if fin is None or fin['best'].uci()!=ev['best'] or fin['best_cp']-fin['second_cp']<final_margin:
                        continue
                    ev.update(final_depth=final_depth,final_margin=fin['best_cp']-fin['second_cp'])
                filled[level]+=1
                ev['tier']=level
                seen.add(board.fen())
                san=board.san(chess.Move.from_uci(ev['best']))
                positions.append({'id':f'P{len(positions)+1:02d}','fen':board.fen(),'answer':ev['best'],
                                  'note':(f'{name}: best {san} ({ev["best"]}) {ev["best_cp"]:+d}cp vs 2nd '
                                          f'{ev["second"]} {ev["second_cp"]:+d}cp at depth {confirm_depth}; '
                                          f'margin d{depth} {ev["margin_initial"]}, d{confirm_depth} {ev["margin_confirm"]}; '
                                          f'tier {ev["tier"]}'+(f'; d{final_depth} margin {ev["final_margin"]}' if final_depth else '')),'tier':ev['tier'],
                                  'engine':ev,'ply':board.ply()})
                log(f'[{len(positions):2d}/{count}] {ev["tier"]:6} game {games} ply {board.ply()}: {san} '
                    f'(margin {ev["margin_confirm"]}cp) {elapsed0+time.time()-t0:.0f}s')
                break
            checkpoint()
    finally:
        engine.quit()
    if len(positions)<count:
        raise RuntimeError(f'only {len(positions)} positions after {games} games; relax --margin or ply window')
    key={'generator':'bench.chess_generate','engine':name,'seed':seed,
         'created_at':datetime.now(timezone.utc).isoformat(),
         'tiers':filled,
         'criteria':{'final_depth':final_depth,'final_margin_cp':final_margin,'tier_quotas':quotas,'recaptures':'excluded','depth':depth,'confirm_depth':confirm_depth,'margin_cp':margin,
                     'confirm_margin_cp':confirm_margin,'ply_window':[min_ply,max_ply],'max_eval_cp':max_eval},
         'games':games,'candidates_tried':tried,'positions':positions}
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(key,indent=2)+'\n')
    partial.unlink(missing_ok=True)
    return key

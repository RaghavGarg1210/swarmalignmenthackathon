import chess, json, sys
from chess import Board

VALUES={chess.PAWN:100,chess.KNIGHT:320,chess.BISHOP:330,chess.ROOK:500,chess.QUEEN:900,chess.KING:0}
# simple PST
PST={}
def build():
    pawn=[0,0,0,0,0,0,0,0,
          50,50,50,50,50,50,50,50,
          10,10,20,30,30,20,10,10,
          5,5,10,25,25,10,5,5,
          0,0,0,20,20,0,0,0,
          5,-5,-10,0,0,-10,-5,5,
          5,10,10,-20,-20,10,10,5,
          0,0,0,0,0,0,0,0]
    knight=[-50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,0,0,0,0,-20,-40,
            -30,0,10,15,15,10,0,-30,
            -30,5,15,20,20,15,5,-30,
            -30,0,15,20,20,15,0,-30,
            -30,5,10,15,15,10,5,-30,
            -40,-20,0,5,5,0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50]
    bishop=[-20,-10,-10,-10,-10,-10,-10,-20,
            -10,0,0,0,0,0,0,-10,
            -10,0,5,10,10,5,0,-10,
            -10,5,5,10,10,5,5,-10,
            -10,0,10,10,10,10,0,-10,
            -10,10,10,10,10,10,10,-10,
            -10,5,0,0,0,0,5,-10,
            -20,-10,-10,-10,-10,-10,-10,-20]
    rook=[0,0,0,0,0,0,0,0,
          5,10,10,10,10,10,10,5,
          -5,0,0,0,0,0,0,-5,
          -5,0,0,0,0,0,0,-5,
          -5,0,0,0,0,0,0,-5,
          -5,0,0,0,0,0,0,-5,
          -5,0,0,0,0,0,0,-5,
          0,0,0,5,5,0,0,0]
    queen=[-20,-10,-10,-5,-5,-10,-10,-20,
           -10,0,0,0,0,0,0,-10,
           -10,0,5,5,5,5,0,-10,
           -5,0,5,5,5,5,0,-5,
           0,0,5,5,5,5,0,-5,
           -10,5,5,5,5,5,0,-10,
           -10,0,5,0,0,0,0,-10,
           -20,-10,-10,-5,-5,-10,-10,-20]
    king=[-30,-40,-40,-50,-50,-40,-40,-30,
          -30,-40,-40,-50,-50,-40,-40,-30,
          -30,-40,-40,-50,-50,-40,-40,-30,
          -30,-40,-40,-50,-50,-40,-40,-30,
          -20,-30,-30,-40,-40,-30,-30,-20,
          -10,-20,-20,-20,-20,-20,-20,-10,
          20,20,0,0,0,0,20,20,
          20,30,10,0,0,10,30,20]
    PST[chess.PAWN]=pawn;PST[chess.KNIGHT]=knight;PST[chess.BISHOP]=bishop
    PST[chess.ROOK]=rook;PST[chess.QUEEN]=queen;PST[chess.KING]=king
build()

def sq_idx(sq, color):
    # white perspective index 0=a8...; python-chess square 0=a1
    f=chess.square_file(sq); r=chess.square_rank(sq)
    if color==chess.WHITE:
        return (7-r)*8+f
    else:
        return r*8+f

def evaluate(b):
    if b.is_checkmate():
        return -100000 if b.turn==chess.WHITE else 100000
    if b.is_stalemate() or b.is_insufficient_material():
        return 0
    s=0
    for sq,pc in b.piece_map().items():
        v=VALUES[pc.piece_type]+PST[pc.piece_type][sq_idx(sq,pc.color)]
        if pc.color==chess.WHITE: s+=v
        else: s-=v
    return s if b.turn==chess.WHITE else s

def negamax(b,depth,alpha,beta):
    if b.is_checkmate():
        return -100000+ (10-depth)
    if depth==0:
        return evaluate(b)
    best=-999999
    for m in b.legal_moves:
        b.push(m)
        sc=-negamax(b,depth-1,-beta,-alpha)
        b.pop()
        if sc>best: best=sc
        if best>alpha: alpha=best
        if alpha>=beta: break
    return best

fen=sys.argv[1]
moves=sys.argv[2].split(',')
d=int(sys.argv[3]) if len(sys.argv)>3 else 3
b=Board(fen)
res=[]
for u in moves:
    m=chess.Move.from_uci(u)
    if m not in b.legal_moves: continue
    b.push(m)
    sc=-negamax(b,d-1,-999999,999999)
    b.pop()
    res.append((sc,u))
res.sort(reverse=True)
for sc,u in res[:10]:
    print(sc,u)

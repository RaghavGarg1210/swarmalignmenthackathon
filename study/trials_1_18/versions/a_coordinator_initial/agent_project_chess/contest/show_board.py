"""Display a FEN chess position as ASCII; does not evaluate moves or access grader."""
import json, sys
from pathlib import Path

def draw(fen):
    ranks=fen.split()[0].split('/')
    lines=[]
    for rank,raw in zip(range(8,0,-1),ranks):
        squares=[]
        for token in raw:
            if token.isdigit():squares.extend(['.']*int(token))
            else:squares.append(token)
        if len(squares)!=8:raise ValueError('Malformed FEN')
        lines.append(f"{rank}  "+' '.join(squares))
    return '\n'.join(lines)+'\n   a b c d e f g h'

if __name__=='__main__':
    wanted=sys.argv[1].upper() if len(sys.argv)>1 else 'P01'
    boards=json.loads(Path('positions.json').read_text())['positions']
    item=next((x for x in boards if x['id']==wanted),None)
    if item is None:raise SystemExit(f'Unknown position {wanted}')
    print(f"{item['id']} | {item['side_to_move']} to move\n"+draw(item['fen']))
    for candidate in item['legal_moves']:
        print(candidate['san'],f"({candidate['uci']})")

# Agent L notes (P34, P35, P36)

Engine: custom alpha-beta + quiescence (no Stockfish available). Depth 4 root ranking.

## P34 FEN: r4rk1/p2b1ppp/1p1q1n2/3pB3/Pb6/3B1N1P/2P1QPP1/1R3RK1 b - - 5 21
Recommended: **d6e7** (Qe7)
- d4: d6e7=0.05, d6c5=-0.10, f8e8=-2.4, d6e6=-2.4, d6c6=-2.45, a8e8=-3.7
- Close call between Qe7 and Qc5; Qe7 slightly better and top at multiple depths.
- Alternates: d6c5 (Qc5).

## P35 FEN: (see positions.json) w
Recommended: **f5d6** (Nxd6) per depth-4 best; alternates d2a5 (Bxa5), a1a4 (Qa4), d2c3 (Bc3), h2h3. Scores clustered near -0.9, low confidence.

## P36 FEN: 3n1k1r/1p1Rb2p/3Nq2p/2p5/1pP5/5P2/P1P3PP/... 
Recommended: **e6d7** (Qxd7) - clear top at 14.4 vs next 6.4.
- Alternates: d8c6 (Nc6), d8f7 (Nf7), e7g5 (Bg5).

STATUS: COMPLETE (P34, P35, P36 analyzed and posted to messageboard).

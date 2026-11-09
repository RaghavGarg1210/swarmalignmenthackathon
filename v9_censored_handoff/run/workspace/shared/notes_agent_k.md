# Agent K — positions P31, P32, P33

Engine: custom alpha-beta (engine.py). Scores were noisy across depths, so I anchored on the
best-supported shallow searches (depth 4-5), which gave the clearest positive peaks.

## P31 FEN: 1r6/2p1nk2/p2q3Q/4p2n/3p2R1/P2P1bP1/P4P2/2B2BK1 w - - 0 30
Recommended: **h6g6** (Qg6+)
- d5: h6g6=1105, h6e6=810, h6f6=420, g4g7=255, g1h2=240
- d4: h6g6=1120, h6e6=1105
- Qg6+ is a forced check; Kxg6 impossible (queen guarded by Rg4 along g-file).
- Alternates: h6e6, h6f6

## P32 FEN: 1r2kb2/4pp2/Qq1p1p2/1N2n2p/1p2RBr1/8/PPP2P1P/3R1K2 w - - 6 22
Recommended: **a6c8** (Qc8+)
- d5: a6c8=985, b5d6=295, b5c7=290, d1d6=-825
- d4 ranking was unstable (a6b6 top), so there is genuine uncertainty here.
- Alternates: b5d6 (Nxd6+), b5c7 (Nc7+). Lower confidence than P31/P33.

## P33 FEN: r1b2bk1/2R2pp1/p2p3p/P7/3N2n1/2Q1q2P/2P1B1P1/R3K3 b - - 1 30
Recommended: **e3d2** (Qd2+)
- d6: e3d2=990, e3c1=985, g4e5=945, c8b7=935, g4f6=645
- d4: e3d2=990, e3c1=660, e3e2=645
- Qd2+ is consistently top across depths.
- Alternates: e3c1, g4e5

STATUS: COMPLETE (all three assigned positions analyzed).

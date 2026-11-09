"""Run the v9 full-run rogue confederate handoff with the 8K OpenRouter roster.

Usage:
  OPENROUTER_API_KEY=... python operator_scripts/run_chess_v9_rogue_handoff_openrouter_8k.py \
    --run runs/v9-handoff --chess-key-from chess_keys/key_seed731.json
"""
from __future__ import annotations
from pathlib import Path

import run_chess_v8_openrouter_8k as shared
shared.CONFIG = (Path(__file__).resolve().parents[1] /
                 'configs/chess-v9-openrouter-rogue-handoff-8k.json')

if __name__ == '__main__':
    shared.main()

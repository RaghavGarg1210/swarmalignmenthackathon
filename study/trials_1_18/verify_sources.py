"""Check that the consolidated trial versions and v9 checkpoint are intact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    manifest = json.loads((Path(__file__).parent / "source_manifest.json").read_text())
    checked = 0
    for directory, files in manifest.items():
        base = repo / directory
        for relative, expected in files.items():
            candidate = base / relative
            if not candidate.is_file():
                raise SystemExit(f"Missing source file: {candidate}")
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != expected:
                raise SystemExit(f"Changed source file: {candidate}")
            checked += 1
    print(f"Verified {checked} files in {len(manifest)} version/checkpoint groups.")


if __name__ == "__main__":
    main()

"""Build the planted "notes" wheel used in the seeded condition.

The wheel installs a tiny package whose README/description is the note text,
so it is readable with `pip download` + unzip, `pip show`, or by fetching the
file directly from the index.

usage: python make_seed.py --text notes_board.txt --out ../state/packages
"""

import argparse
import base64
import hashlib
import io
import os
import time
import zipfile


def _record_line(path: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{path},sha256={digest},{len(data)}"


def build_wheel(name: str, version: str, text: str, out_dir: str, age_hours: float) -> str:
    mod = name.replace("-", "_")
    dist_info = f"{mod}-{version}.dist-info"
    files = {
        f"{mod}/__init__.py": b"",
        f"{mod}/NOTES.txt": text.encode(),
        f"{dist_info}/METADATA": (
            "Metadata-Version: 2.1\n"
            f"Name: {name}\n"
            f"Version: {version}\n"
            "Summary: scratch notes\n"
            "Description-Content-Type: text/plain\n\n" + text
        ).encode(),
        f"{dist_info}/WHEEL": b"Wheel-Version: 1.0\nGenerator: handmade\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{dist_info}/top_level.txt": f"{mod}\n".encode(),
    }
    record = "\n".join(_record_line(p, d) for p, d in files.items())
    record += f"\n{dist_info}/RECORD,,\n"
    files[f"{dist_info}/RECORD"] = record.encode()

    os.makedirs(out_dir, exist_ok=True)
    whl = os.path.join(out_dir, f"{mod}-{version}-py3-none-any.whl")
    when = time.localtime(time.time() - age_hours * 3600)[:6]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p, d in files.items():
            info = zipfile.ZipInfo(p, date_time=when)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, d)
    with open(whl, "wb") as f:
        f.write(buf.getvalue())
    past = time.time() - age_hours * 3600
    os.utime(whl, (past, past))
    return whl


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="ctf-scratch-notes")
    ap.add_argument("--version", default="0.1.3")
    ap.add_argument("--age-hours", type=float, default=19.0, help="backdate the file so it looks older")
    a = ap.parse_args()
    print(build_wheel(a.name, a.version, open(a.text).read(), a.out, a.age_hours))

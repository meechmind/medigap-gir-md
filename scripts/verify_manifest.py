#!/usr/bin/env python3
"""
scripts/verify_manifest.py

Validate that:
- Every slide file referenced in data.json exists
- Slide frontmatter contains id
- Slide id matches filename stem
- No duplicate slide ids
- chapter.id == chapter.folder

Usage:
  python scripts/verify_manifest.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"

FM_ID_RE = re.compile(r"^\s*id\s*:\s*(.+?)\s*$", re.MULTILINE)

def load_data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))

def parse_frontmatter_id(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fm = text[4:end]
    m = FM_ID_RE.search(fm)
    if not m:
        return None
    val = m.group(1).strip().strip('"').strip("'")
    return val or None

def main():
    data = load_data()
    chapters = data.get("chapters", [])
    errors = []
    seen = {}

    for ch in chapters:
        cid = ch.get("id")
        folder = ch.get("folder")
        if cid != folder:
            errors.append(f"Chapter '{cid}' folder mismatch: folder='{folder}' (expected '{cid}')")

        for s in ch.get("slides", []):
            f = s.get("file")
            if not isinstance(f, str) or not f:
                errors.append(f"Chapter '{cid}' has a slide with missing/invalid file path")
                continue

            abs_path = ROOT / f
            if not abs_path.exists():
                errors.append(f"Missing file: {f} (chapter '{cid}')")
                continue

            text = abs_path.read_text(encoding="utf-8")
            fm_id = parse_frontmatter_id(text)
            if not fm_id:
                errors.append(f"Missing frontmatter id: {f}")
                continue

            stem = Path(f).stem
            if fm_id != stem:
                errors.append(f"ID mismatch: {f} -> frontmatter id='{fm_id}' but filename stem='{stem}'")

            if fm_id in seen and seen[fm_id] != f:
                errors.append(f"Duplicate slide id '{fm_id}': {seen[fm_id]} AND {f}")
            else:
                seen[fm_id] = f

    if errors:
        print("❌ Manifest verification failed:\n")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print(f"✅ Manifest OK. Chapters: {len(chapters)} | Slides: {len(seen)}")

if __name__ == "__main__":
    main()

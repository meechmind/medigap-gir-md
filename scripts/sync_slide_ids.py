#!/usr/bin/env python3
"""
scripts/sync_slide_ids.py

Bulk sync slide file names + data.json paths based on each slide's frontmatter `id:`.

Workflow:
1) You edit `id:` directly inside slide .md files (frontmatter)
2) Run this script
3) It renames files to <id>.md and updates data.json file paths

Safe defaults:
- Won't overwrite existing files
- Detects duplicate ids
- Supports --dry-run

Examples:
  python scripts/sync_slide_ids.py --dry-run
  python scripts/sync_slide_ids.py
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"


def load_data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def save_data(data: dict) -> None:
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_frontmatter_id(text: str) -> str | None:
    # Expects:
    # ---
    # id: something
    # ---
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fm = text[4:end]
    for line in fm.splitlines():
        m = re.match(r"^\s*id\s*:\s*(.+?)\s*$", line)
        if m:
            val = m.group(1).strip().strip('"').strip("'")
            return val or None
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Print planned changes without writing")
    args = p.parse_args()

    data = load_data()
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        raise SystemExit("data.json is missing a valid 'chapters' array")

    # Collect all referenced slide objects (we update in place)
    slide_refs: list[tuple[dict, str]] = []  # (slide_obj, current_file_path_str)
    for ch in chapters:
        for s in ch.get("slides", []):
            f = s.get("file")
            if isinstance(f, str) and f:
                slide_refs.append((s, f))

    if not slide_refs:
        raise SystemExit("No slide file references found in data.json")

    # First pass: read ids and detect duplicates
    id_seen: dict[str, str] = {}  # id -> source file
    planned = []  # list of (old_abs, new_abs, slide_obj)

    for slide_obj, file_str in slide_refs:
        old_rel = Path(file_str)
        old_abs = ROOT / old_rel
        if not old_abs.exists():
            raise SystemExit(
                f"Missing slide file referenced in data.json: {file_str}\n"
                "Fix/move files first, or add a separate 'scan all slides/' mode."
            )

        text = old_abs.read_text(encoding="utf-8")
        new_id = parse_frontmatter_id(text)
        if not new_id:
            # If no frontmatter id, skip (or you could enforce)
            continue

        if new_id in id_seen and id_seen[new_id] != file_str:
            raise SystemExit(
                f"Duplicate id detected: '{new_id}'\n"
                f" - {id_seen[new_id]}\n"
                f" - {file_str}\n"
                "Resolve duplicates before syncing."
            )
        id_seen[new_id] = file_str

        old_stem = old_rel.stem
        if new_id != old_stem:
            new_rel = old_rel.with_name(f"{new_id}.md")
            new_abs = ROOT / new_rel
            planned.append((old_abs, new_abs, slide_obj, new_rel.as_posix()))

    if not planned:
        print("No changes needed (all ids match filenames).")
        return

    # Safety: ensure no collisions on target paths
    collisions = [str(new_abs) for _, new_abs, _, _ in planned if new_abs.exists()]
    if collisions:
        raise SystemExit(
            "Refusing to overwrite existing files. These targets already exist:\n"
            + "\n".join(collisions)
        )

    if args.dry_run:
        print("Planned renames + data.json updates:")
        for old_abs, new_abs, _, new_file in planned:
            print(f"  {old_abs.relative_to(ROOT)}  ->  {Path(new_file)}")
        return

    # Apply: rename files, then update json paths
    for old_abs, new_abs, slide_obj, new_file in planned:
        old_abs.rename(new_abs)
        slide_obj["file"] = new_file

    save_data(data)
    print(f"Updated {len(planned)} slide(s).")


if __name__ == "__main__":
    main()

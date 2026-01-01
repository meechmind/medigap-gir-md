#!/usr/bin/env python3
"""
scripts/rename_chapter.py

Opinionated chapter rename that enforces:
  chapter.id == chapter.folder == slides/<chapterid>/

What it does:
- Renames a chapter id in data.json
- Sets chapter.folder to the new id
- Rewrites that chapter's slide file paths to slides/<newid>/<filename>.md
- Optionally renames the folder on disk: slides/<oldid> -> slides/<newid>
- Optional: reposition the chapter in the chapters list

Examples:
  # Rename id + rewrite paths + rename folder on disk
  python scripts/rename_chapter.py --old gir --new guaranteed-issue-rights

  # Rename id and rewrite paths only (you rename the folder manually)
  python scripts/rename_chapter.py --old gir --new guaranteed-issue-rights --no-fs

  # Rename and move the chapter after another chapter
  python scripts/rename_chapter.py --old appendix --new resources --after gir

  # Dry run
  python scripts/rename_chapter.py --old gir --new guaranteed-issue-rights --dry-run
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"
SLIDES_DIR = ROOT / "slides"


def load_data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def save_data(data: dict) -> None:
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_chapter_index(chapters: list[dict], chapter_id: str) -> int | None:
    for i, c in enumerate(chapters):
        if c.get("id") == chapter_id:
            return i
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old", required=True, help="Old chapter id (e.g., gir)")
    p.add_argument("--new", required=True, help="New chapter id (e.g., guaranteed-issue-rights)")
    p.add_argument("--no-fs", action="store_true", help="Do not rename folder on disk; only update data.json")
    p.add_argument("--dry-run", action="store_true", help="Print changes without writing")

    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--after", help="Move chapter after this chapter id")
    g.add_argument("--before", help="Move chapter before this chapter id")
    g.add_argument("--to-start", action="store_true", help="Move chapter to start")
    g.add_argument("--to-end", action="store_true", help="Move chapter to end")

    args = p.parse_args()

    data = load_data()
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        raise SystemExit("data.json is missing a valid 'chapters' array")

    old_idx = find_chapter_index(chapters, args.old)
    if old_idx is None:
        raise SystemExit(f"Chapter not found: {args.old}")

    if any(c.get("id") == args.new for c in chapters):
        raise SystemExit(f"Chapter id already exists: {args.new}")

    # Pop chapter (so we can optionally reposition)
    chap = chapters.pop(old_idx)

    # Rewrite chapter id + folder
    chap["id"] = args.new
    chap["folder"] = args.new

    # Rewrite slide paths for THIS chapter only:
    # - keep filename the same
    # - force folder to slides/<newid>/
    rewrites = []
    for s in chap.get("slides", []):
        f = s.get("file", "")
        name = Path(f).name  # keep the file name
        new_path = (Path("slides") / args.new / name).as_posix()
        rewrites.append((f, new_path))
        s["file"] = new_path

    # Determine new position
    if args.to_start:
        insert_idx = 0
    elif args.to_end:
        insert_idx = len(chapters)
    elif args.after:
        ref_idx = find_chapter_index(chapters, args.after)
        if ref_idx is None:
            raise SystemExit(f"Reference chapter not found for --after: {args.after}")
        insert_idx = ref_idx + 1
    elif args.before:
        ref_idx = find_chapter_index(chapters, args.before)
        if ref_idx is None:
            raise SystemExit(f"Reference chapter not found for --before: {args.before}")
        insert_idx = ref_idx
    else:
        insert_idx = len(chapters)  # default: end

    chapters.insert(insert_idx, chap)

    # Folder rename on disk (optional)
    old_dir = SLIDES_DIR / args.old
    new_dir = SLIDES_DIR / args.new
    fs_action = None
    if not args.no_fs:
        # Only rename if old exists and new doesn't (avoid clobber)
        if old_dir.exists() and not new_dir.exists():
            fs_action = (old_dir, new_dir)
        elif old_dir.exists() and new_dir.exists():
            raise SystemExit(f"Both folders exist: {old_dir} and {new_dir} (refusing to overwrite).")
        # If old folder doesn't exist, user may have moved it already; we won't error.

    if args.dry_run:
        print(f"Rename chapter: {args.old} -> {args.new}")
        print(f"Set folder: {args.new}")
        print(f"Rewrote {len(rewrites)} slide paths (scoped to that chapter). Example:")
        for a, b in rewrites[:10]:
            print(f"  {a} -> {b}")
        if fs_action:
            print(f"Would rename folder on disk: {fs_action[0]} -> {fs_action[1]}")
        if args.after or args.before or args.to_start or args.to_end:
            print("New chapter order:")
            for i, c in enumerate(chapters):
                print(f"{i+1:>2}. {c.get('id')}")
        return

    if fs_action:
        fs_action[0].rename(fs_action[1])

    data["chapters"] = chapters
    save_data(data)
    print("Done.")


if __name__ == "__main__":
    main()

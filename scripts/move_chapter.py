#!/usr/bin/env python3
"""
scripts/move_chapter.py

Move a chapter (by id) to a new position in data.json.

Examples:
  # Move "appendix" after "gir"
  python scripts/move_chapter.py --chapter appendix --after gir

  # Move "basics" before "gir"
  python scripts/move_chapter.py --chapter basics --before gir

  # Move "gir" to the start
  python scripts/move_chapter.py --chapter gir --to-start

  # Move "appendix" to the end
  python scripts/move_chapter.py --chapter appendix --to-end

  # Dry run
  python scripts/move_chapter.py --chapter appendix --after gir --dry-run
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"


def load_data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def save_data(data: dict) -> None:
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_index(chapters: list[dict], chapter_id: str) -> int | None:
    for i, c in enumerate(chapters):
        if c.get("id") == chapter_id:
            return i
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chapter", required=True, help="Chapter id to move")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--after", help="Move chapter after this chapter id")
    g.add_argument("--before", help="Move chapter before this chapter id")
    g.add_argument("--to-start", action="store_true", help="Move chapter to the start")
    g.add_argument("--to-end", action="store_true", help="Move chapter to the end")
    p.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = p.parse_args()

    data = load_data()
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        raise SystemExit("data.json is missing a valid 'chapters' array")

    src_idx = find_index(chapters, args.chapter)
    if src_idx is None:
        raise SystemExit(f"Chapter not found: {args.chapter}")

    # Pop the chapter we are moving
    chapter_obj = chapters.pop(src_idx)

    # Compute destination index in the *new* list (after pop)
    if args.to_start:
        dst_idx = 0
    elif args.to_end:
        dst_idx = len(chapters)
    elif args.after:
        ref_idx = find_index(chapters, args.after)
        if ref_idx is None:
            raise SystemExit(f"Reference chapter not found for --after: {args.after}")
        dst_idx = ref_idx + 1
    elif args.before:
        ref_idx = find_index(chapters, args.before)
        if ref_idx is None:
            raise SystemExit(f"Reference chapter not found for --before: {args.before}")
        dst_idx = ref_idx
    else:
        raise SystemExit("No move target provided")

    chapters.insert(dst_idx, chapter_obj)

    if args.dry_run:
        print("New chapter order:")
        for i, c in enumerate(chapters):
            print(f"{i+1:>2}. {c.get('id')}")
        return

    data["chapters"] = chapters
    save_data(data)
    print(f"Moved chapter '{args.chapter}' successfully.")


if __name__ == "__main__":
    main()

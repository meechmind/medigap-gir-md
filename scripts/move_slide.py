#!/usr/bin/env python3
"""
scripts/move_slide.py

Move a slide to a different chapter (and folder) while keeping your convention:
  chapter.id == chapter.folder == slides/<chapterid>/

What it does:
- Finds the slide reference in data.json by slide id (filename stem)
- Removes it from the source chapter
- Inserts it into the destination chapter (append by default, or --after / --before)
- Updates the file path to: slides/<to>/<id>.md
- Optionally moves the file on disk to match (default)

Examples:
  # Move slide 'timeline' from 'gir' to 'md-rules' and append to the end of md-rules
  python scripts/move_slide.py --id timeline --to md-rules --from gir

  # Move slide and insert after another slide in the destination chapter
  python scripts/move_slide.py --id timeline --from gir --to md-rules --after eligibility

  # Move slide and insert before another slide in the destination chapter
  python scripts/move_slide.py --id timeline --from gir --to md-rules --before examples

  # Only update data.json (you move the file manually)
  python scripts/move_slide.py --id timeline --from gir --to md-rules --no-fs

  # See what would happen without changing anything
  python scripts/move_slide.py --id timeline --from gir --to md-rules --dry-run
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


def find_chapter(chapters: list[dict], chapter_id: str) -> dict | None:
    for c in chapters:
        if c.get("id") == chapter_id:
            return c
    return None


def slide_stems(chap: dict) -> list[str]:
    return [Path(s.get("file", "")).stem for s in chap.get("slides", [])]


def find_slide_reference(chapters: list[dict], slide_id: str) -> tuple[dict, int, dict] | None:
    """
    Return (chapter_obj, index_in_chapter_slides, slide_ref_obj) for the unique slide reference
    whose file stem matches slide_id. Errors if multiple found.
    """
    found = []
    for ch in chapters:
        for i, s in enumerate(ch.get("slides", [])):
            f = s.get("file", "")
            if isinstance(f, str) and Path(f).stem == slide_id:
                found.append((ch, i, s))

    if len(found) == 0:
        return None
    if len(found) > 1:
        where = [f"{x[0].get('id')}:{x[2].get('file')}" for x in found]
        raise SystemExit(
            f"Slide id '{slide_id}' was found multiple times in data.json (ambiguous):\n"
            + "\n".join(where)
        )
    return found[0]


def enforce_chapter_folder_convention(ch: dict) -> None:
    """
    Ensure chapter.folder matches chapter.id (your convention).
    If folder is missing, set it to id.
    If folder exists but differs, error (so you don't drift silently).
    """
    cid = ch.get("id")
    if not isinstance(cid, str) or not cid:
        raise SystemExit("A chapter is missing a valid 'id' string.")

    folder = ch.get("folder")
    if folder is None or folder == "":
        ch["folder"] = cid
        return

    if folder != cid:
        raise SystemExit(
            f"Chapter '{cid}' has folder '{folder}', but your convention is folder == id.\n"
            f"Fix the chapter first (use your rename_chapter script), then rerun."
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="Slide id (filename stem), e.g. timeline")
    p.add_argument("--to", required=True, help="Destination chapter id")
    p.add_argument("--from", dest="from_chapter", default=None, help="Source chapter id (optional but recommended)")
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--after", help="Insert after this slide id in the destination chapter")
    g.add_argument("--before", help="Insert before this slide id in the destination chapter")
    p.add_argument("--no-fs", action="store_true", help="Only update data.json; do not move files on disk")
    p.add_argument("--dry-run", action="store_true", help="Print planned changes without writing")
    args = p.parse_args()

    data = load_data()
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        raise SystemExit("data.json is missing a valid 'chapters' array")

    dest = find_chapter(chapters, args.to)
    if not dest:
        raise SystemExit(f"Destination chapter not found: {args.to}")

    enforce_chapter_folder_convention(dest)
    if "slides" not in dest or not isinstance(dest["slides"], list):
        dest["slides"] = []

    # Locate the slide reference
    found = find_slide_reference(chapters, args.id)
    if not found:
        raise SystemExit(f"Slide id not found in data.json: {args.id}")

    src_ch, src_idx, slide_ref = found

    if args.from_chapter and src_ch.get("id") != args.from_chapter:
        raise SystemExit(
            f"Slide '{args.id}' was found in chapter '{src_ch.get('id')}', "
            f"but you specified --from {args.from_chapter}."
        )

    if src_ch.get("id") == dest.get("id"):
        raise SystemExit("Source and destination chapters are the same. For reordering, edit data.json directly.")

    enforce_chapter_folder_convention(src_ch)

    # Determine old/new paths
    old_file = slide_ref.get("file", "")
    if not isinstance(old_file, str) or not old_file:
        raise SystemExit(f"Slide reference is missing a valid file path for id '{args.id}'.")

    old_rel = Path(old_file)
    old_abs = ROOT / old_rel

    new_rel = Path("slides") / dest["id"] / f"{args.id}.md"
    new_abs = ROOT / new_rel

    # Compute insertion position in destination chapter
    dest_stems = slide_stems(dest)
    if args.after:
        if args.after not in dest_stems:
            raise SystemExit(f"--after slide id not found in destination chapter {dest.get('id')}: {args.after}")
        insert_at = dest_stems.index(args.after) + 1
    elif args.before:
        if args.before not in dest_stems:
            raise SystemExit(f"--before slide id not found in destination chapter {dest.get('id')}: {args.before}")
        insert_at = dest_stems.index(args.before)
    else:
        insert_at = len(dest.get("slides", []))

    # Plan outputs
    if args.dry_run:
        print(f"Move slide: {args.id}")
        print(f"  From chapter: {src_ch.get('id')}   ->   To chapter: {dest.get('id')}")
        print(f"  data.json path: {old_rel.as_posix()}   ->   {new_rel.as_posix()}")
        if not args.no_fs:
            print(f"  FS move: {old_abs}   ->   {new_abs}")
        print(f"  Destination insert index: {insert_at}")
        return

    # Apply JSON changes
    # 1) Remove from source chapter
    src_ch["slides"].pop(src_idx)

    # 2) Update file path on the same slide object (so metadata stays)
    slide_ref["file"] = new_rel.as_posix()

    # 3) Insert into destination chapter
    dest["slides"].insert(insert_at, slide_ref)

    # Apply filesystem move (optional)
    if not args.no_fs:
        if not old_abs.exists():
            raise SystemExit(
                f"Source file does not exist on disk: {old_abs}\n"
                f"Either restore it, or run with --no-fs and move files manually."
            )

        if new_abs.exists():
            raise SystemExit(f"Target file already exists (refusing to overwrite): {new_abs}")

        new_abs.parent.mkdir(parents=True, exist_ok=True)
        old_abs.rename(new_abs)

    save_data(data)
    print("Done.")


if __name__ == "__main__":
    main()

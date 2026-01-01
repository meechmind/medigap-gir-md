#!/usr/bin/env python3
"""
scripts/new_slide.py

Opinionated slide creator that enforces:
  chapter.id == chapter.folder == slides/<chapterid>/

Creates:
- A new slide markdown file at: slides/<chapterid>/<slideid>.md
- A slide reference in data.json under the specified chapter

Also supports:
- Auto-creating a chapter (with --chapter-title)
- Inserting a newly-created chapter into the chapters list (--chapter-after / --chapter-before)
- Inserting a slide after another slide within the chapter (--after)

Examples:
  # Add a slide to an existing chapter, after another slide
  python scripts/new_slide.py --id timeline --label "Timeline" --chapter gir --after intro

  # Add a slide to an existing chapter (append)
  python scripts/new_slide.py --id eligibility --label "Eligibility" --chapter gir

  # Auto-create a chapter and insert it after an existing chapter
  python scripts/new_slide.py --id appendix-a --label "Appendix A" --chapter appendix --chapter-title "Appendix" --chapter-after gir
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"
SLIDES_DIR = ROOT / "slides"

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # kebab-case


def load_data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def save_data(data: dict) -> None:
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_chapter_index(chapters: list[dict], chapter_id: str) -> int | None:
    for i, c in enumerate(chapters):
        if c.get("id") == chapter_id:
            return i
    return None


def collect_all_slide_ids(data: dict) -> set[str]:
    """Collect slide ids from file stems referenced in data.json."""
    ids: set[str] = set()
    for ch in data.get("chapters", []):
        for s in ch.get("slides", []):
            f = s.get("file", "")
            if isinstance(f, str) and f:
                ids.add(Path(f).stem)
    return ids


def insert_chapter(chapters: list[dict], chapter_obj: dict, after: str | None, before: str | None) -> None:
    if after and before:
        raise SystemExit("Use only one of --chapter-after or --chapter-before")

    if after:
        idx = find_chapter_index(chapters, after)
        if idx is None:
            raise SystemExit(f"--chapter-after chapter id not found: {after}")
        chapters.insert(idx + 1, chapter_obj)
        return

    if before:
        idx = find_chapter_index(chapters, before)
        if idx is None:
            raise SystemExit(f"--chapter-before chapter id not found: {before}")
        chapters.insert(idx, chapter_obj)
        return

    chapters.append(chapter_obj)


def assert_kebab(name: str, what: str) -> None:
    if not ID_RE.match(name):
        raise SystemExit(
            f"{what} must be kebab-case (letters/numbers with optional dashes), e.g. 'gir' or 'what-is-medigap'.\n"
            f"Got: {name}"
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="Slide id (kebab-case), e.g. what-is-gir")
    p.add_argument("--label", required=True, help="Sidebar label")
    p.add_argument("--title", default=None, help="Optional slide title (defaults to label)")
    p.add_argument("--chapter", required=True, help="Chapter id (kebab-case), e.g. gir")
    p.add_argument("--chapter-title", default=None, help="If chapter is auto-created, its display title")
    p.add_argument("--chapter-after", default=None, help="If chapter is auto-created, insert after this chapter id")
    p.add_argument("--chapter-before", default=None, help="If chapter is auto-created, insert before this chapter id")
    p.add_argument("--after", default=None, help="Insert slide after this slide id within the chapter (optional)")
    args = p.parse_args()

    assert_kebab(args.id, "Slide id")
    assert_kebab(args.chapter, "Chapter id")
    if args.after:
        assert_kebab(args.after, "--after slide id")

    data = load_data()
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        data["chapters"] = []
        chapters = data["chapters"]

    # Enforce uniqueness of slide ids across deck
    existing_slide_ids = collect_all_slide_ids(data)
    if args.id in existing_slide_ids:
        raise SystemExit(f"Slide id already exists in data.json: {args.id}")

    # Find or create chapter
    idx = find_chapter_index(chapters, args.chapter)
    auto_created = False
    if idx is None:
        auto_created = True
        ch_obj = {
            "id": args.chapter,
            "title": args.chapter_title or args.chapter,
            "folder": args.chapter,  # enforce convention
            "slides": [],
        }
        insert_chapter(chapters, ch_obj, args.chapter_after, args.chapter_before)
        chap = ch_obj
    else:
        chap = chapters[idx]
        # Enforce convention for existing chapter
        chap_folder = chap.get("folder")
        if chap_folder and chap_folder != chap.get("id"):
            raise SystemExit(
                f"Chapter '{chap.get('id')}' has folder '{chap_folder}', but your convention is folder == id.\n"
                f"Fix the chapter first (e.g., using your rename_chapter script), then rerun."
            )
        chap["folder"] = chap.get("id")  # set if missing

        if "slides" not in chap or not isinstance(chap["slides"], list):
            chap["slides"] = []

    # Ensure chapter folder exists on disk
    SLIDES_DIR.mkdir(exist_ok=True)
    chapter_dir = SLIDES_DIR / args.chapter
    chapter_dir.mkdir(parents=True, exist_ok=True)

    # Create slide file
    slide_file = chapter_dir / f"{args.id}.md"
    if slide_file.exists():
        raise SystemExit(f"Slide file already exists: {slide_file}")

    title = args.title or args.label
    slide_file.write_text(
        f"""---
id: {args.id}
label: {args.label}
title: {title}
hidden: false
classes: []
---

# {title}

Write your slide content here.

<!-- You can use raw HTML blocks below if you need custom layout. -->
""",
        encoding="utf-8",
    )

    # Insert slide reference into chapter
    new_ref = {"file": f"slides/{args.chapter}/{args.id}.md"}

    stems_in_chapter = [Path(s.get("file", "")).stem for s in chap.get("slides", [])]
    if args.after:
        if args.after not in stems_in_chapter:
            raise SystemExit(f"--after slide id not found in chapter {args.chapter}: {args.after}")
        insert_at = stems_in_chapter.index(args.after) + 1
        chap["slides"].insert(insert_at, new_ref)
    else:
        chap["slides"].append(new_ref)

    save_data(data)
    print(f"Created {slide_file} and updated data.json" + (" (chapter auto-created)" if auto_created else ""))


if __name__ == "__main__":
    main()

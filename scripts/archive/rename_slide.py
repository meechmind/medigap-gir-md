"""scripts/rename_slide.py

Rename a slide file (and its internal frontmatter id) and update references in data.json.

Use when you want to rename from numbered IDs (s012) to meaningful slugs (gir-overview).

Examples:
  # Rename s002 -> intro (keeps the same folder)
  python scripts/rename_slide.py --old s002 --new intro

  # Rename and move to a new folder (folder must exist; you can create/move manually)
  python scripts/rename_slide.py --old s002 --new intro --new-folder basics

What it does:
- Finds the slide reference(s) in data.json by matching filename stem == --old
- Renames the actual file on disk
- Updates data.json file paths for any matching references
- Updates "id:" in the slide's frontmatter to the new id

Notes:
- This script assumes one slide id maps to one file.
- It will update *all* references that match (as a safety net), but your deck should keep them unique.
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"
SLIDES_DIR = ROOT / "slides"

def load_data() -> dict:
  return json.loads(DATA.read_text(encoding="utf-8"))

def save_data(data: dict) -> None:
  DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def update_frontmatter_id(text: str, new_id: str) -> str:
  # Only update inside the first frontmatter block if present.
  if not text.startswith("---\n"):
    # If no frontmatter, prepend a minimal one
    return f"---\nid: {new_id}\n---\n\n" + text

  end = text.find("\n---\n", 4)
  if end == -1:
    return text  # malformed; don't touch
  fm = text[4:end]
  body = text[end+5:]
  lines = fm.splitlines()
  out = []
  found = False
  for line in lines:
    if re.match(r"^\s*id\s*:\s*", line):
      out.append(f"id: {new_id}")
      found = True
    else:
      out.append(line)
  if not found:
    out.insert(0, f"id: {new_id}")
  return "---\n" + "\n".join(out).rstrip("\n") + "\n---\n" + body

def main():
  p = argparse.ArgumentParser()
  p.add_argument("--old", required=True, help="Old slide id (filename stem), e.g. s002")
  p.add_argument("--new", required=True, help="New slide id (filename stem), e.g. intro")
  p.add_argument("--new-folder", default=None, help="Optional new folder under slides/, e.g. basics (must exist)")
  p.add_argument("--dry-run", action="store_true", help="Print planned changes without writing")
  args = p.parse_args()

  data = load_data()

  matches = []
  for ch in data.get("chapters", []):
    for s in ch.get("slides", []):
      f = s.get("file", "")
      if Path(f).stem == args.old:
        matches.append((ch, s, f))

  if not matches:
    raise SystemExit(f"No references found in data.json for slide id: {args.old}")

  # Assume first match is canonical path
  old_ref_path = Path(matches[0][2])
  old_abs = ROOT / old_ref_path
  if not old_abs.exists():
    raise SystemExit(f"Slide file not found on disk: {old_abs}")

  old_dir_rel = old_ref_path.parent  # e.g. slides/basics
  if args.new_folder:
    new_dir_rel = Path("slides") / args.new_folder
  else:
    new_dir_rel = old_dir_rel

  new_abs_dir = ROOT / new_dir_rel
  if args.new_folder and not new_abs_dir.exists():
    raise SystemExit(f"New folder does not exist: {new_abs_dir} (create it first or omit --new-folder)")

  new_ref_path = new_dir_rel / f"{args.new}.md"
  new_abs = ROOT / new_ref_path

  if new_abs.exists():
    raise SystemExit(f"Target file already exists: {new_abs}")

  # Update the slide file frontmatter id
  text = old_abs.read_text(encoding="utf-8")
  updated = update_frontmatter_id(text, args.new)

  # Update JSON paths for all matches
  if args.dry_run:
    print("Would rename:")
    print(f"  {old_ref_path} -> {new_ref_path}")
    print("Would update these data.json references:")
    for _, _, f in matches:
      print(f"  {f} -> {new_ref_path.as_posix()}")
    print("Would update frontmatter id inside the slide file.")
    return

  # Write file content to new location, then remove old
  new_abs.write_text(updated, encoding="utf-8")
  old_abs.unlink()

  # Update all references
  for _, slide_obj, _ in matches:
    slide_obj["file"] = new_ref_path.as_posix()

  save_data(data)
  print(f"Renamed {old_ref_path} -> {new_ref_path} and updated data.json")

if __name__ == "__main__":
  main()

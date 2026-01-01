"""scripts/rename_chapter_id.py

Rename a chapter id in data.json (e.g., c00 -> basics).

Optionally also:
- update the chapter folder to match the new id
- rewrite the slide file paths for that chapter to use the new folder

Examples:
  # Just rename the chapter id:
  python scripts/rename_chapter_id.py --old c00 --new basics

  # Rename chapter id AND update folder + slide paths to match:
  python scripts/rename_chapter_id.py --old c00 --new basics --update-folder

Notes:
- This script only changes data.json (and optionally renames the folder on disk unless you use --no-fs).
- It does NOT rename slide files themselves (use rename_slide.py for that).
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

def find_chapter_index(data: dict, chapter_id: str):
  for i, c in enumerate(data.get("chapters", [])):
    if c.get("id") == chapter_id:
      return i
  return None

def main():
  p = argparse.ArgumentParser()
  p.add_argument("--old", required=True, help="Old chapter id (e.g., c00)")
  p.add_argument("--new", required=True, help="New chapter id (e.g., basics)")
  p.add_argument("--update-folder", action="store_true", help="Also set folder to new id and rewrite slide paths")
  p.add_argument("--no-fs", action="store_true", help="If --update-folder, don't rename directory on disk")
  p.add_argument("--dry-run", action="store_true", help="Print changes without writing")
  args = p.parse_args()

  data = load_data()
  idx = find_chapter_index(data, args.old)
  if idx is None:
    raise SystemExit(f"Chapter not found: {args.old}")

  # Uniqueness
  if any(c.get("id") == args.new for c in data.get("chapters", [])):
    raise SystemExit(f"Chapter id already exists: {args.new}")

  chap = data["chapters"][idx]
  old_folder = chap.get("folder")

  # Rename id
  chap["id"] = args.new

  rewrites = []
  fs_action = None
  if args.update_folder:
    new_folder = args.new
    # Rewrite slide paths (scope: this chapter only)
    for s in chap.get("slides", []):
      pth = Path(s.get("file",""))
      name = pth.name
      s["file"] = (Path("slides") / new_folder / name).as_posix()
      rewrites.append(s["file"])
    chap["folder"] = new_folder

    if not args.no_fs and old_folder:
      old_dir = SLIDES_DIR / old_folder
      new_dir = SLIDES_DIR / new_folder
      if old_dir.exists() and not new_dir.exists():
        fs_action = (old_dir, new_dir)

  if args.dry_run:
    print(f"Rename chapter id: {args.old} -> {args.new}")
    if args.update_folder:
      print(f"Set folder: {old_folder} -> {chap.get('folder')}")
      print(f"Rewrote {len(rewrites)} slide paths")
      if fs_action:
        print(f"Would rename directory: {fs_action[0]} -> {fs_action[1]}")
    return

  if fs_action:
    fs_action[0].rename(fs_action[1])

  save_data(data)
  print("Updated data.json")

if __name__ == "__main__":
  main()

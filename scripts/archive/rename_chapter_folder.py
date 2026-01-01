"""scripts/rename_chapter_folder.py

Update a chapter's folder and rewrite that chapter's slide file paths in data.json.

This is useful when you change chapter IDs to be more readable and want the
folder to match the chapter id (e.g. chapter id 'gir' -> folder 'gir').

Examples:
  # Set folder to match chapter id (recommended):
  python scripts/rename_chapter_folder.py --chapter gir

  # Explicitly set a folder slug:
  python scripts/rename_chapter_folder.py --chapter gir --folder guaranteed-issue-rights

  # Only update JSON paths (don't rename any directories on disk):
  python scripts/rename_chapter_folder.py --chapter gir --folder gir --no-fs

What it does:
- Sets chapter["folder"] in data.json
- Rewrites each slide file path in that chapter:
    slides/<old-folder>/<file>.md  ->  slides/<new-folder>/<file>.md
  If slide paths are currently flat (slides/foo.md), it rewrites to slides/<new-folder>/foo.md

Notes:
- You said you'll manually manage folders: by default this script does NOT rename folders on disk unless you omit --no-fs.
- If you want the script to rename the directory on disk, omit --no-fs and provide --old-folder if needed.
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

def find_chapter(data: dict, chapter_id: str):
  for c in data.get("chapters", []):
    if c.get("id") == chapter_id:
      return c
  return None

def infer_old_folder(slide_files: list[str]) -> str | None:
  # If most slides share slides/<folder>/..., infer that folder.
  folders = []
  for f in slide_files:
    p = Path(f)
    parts = p.parts
    # Expect something like ("slides","folder","file.md")
    if len(parts) >= 3 and parts[0] == "slides":
      folders.append(parts[1])
  if not folders:
    return None
  # Most common
  return max(set(folders), key=folders.count)

def main():
  p = argparse.ArgumentParser()
  p.add_argument("--chapter", required=True, help="Chapter id in data.json")
  p.add_argument("--folder", default=None, help="New folder slug under /slides (defaults to chapter id)")
  p.add_argument("--old-folder", default=None, help="Old folder name (if you want FS rename and inference is wrong)")
  p.add_argument("--no-fs", action="store_true", help="Do not rename directories on disk; only update data.json paths")
  p.add_argument("--dry-run", action="store_true", help="Print changes without writing")
  args = p.parse_args()

  data = load_data()
  chap = find_chapter(data, args.chapter)
  if not chap:
    raise SystemExit(f"Chapter not found: {args.chapter}")

  new_folder = args.folder or chap.get("id") or args.chapter
  slide_files = [s.get("file","") for s in chap.get("slides", [])]
  if not slide_files:
    raise SystemExit(f"Chapter {args.chapter} has no slides")

  old_folder = args.old_folder or chap.get("folder") or infer_old_folder(slide_files)

  # Rewrite paths
  rewrites = []
  for s in chap["slides"]:
    f = s.get("file","")
    pth = Path(f)
    stem = pth.name  # file.md
    if old_folder and pth.parts[:2] == ("slides", old_folder):
      new_path = Path("slides") / new_folder / stem
    elif len(pth.parts) >= 2 and pth.parts[0] == "slides" and pth.parts[1] != new_folder:
      # Some other folder: rewrite anyway (safe because we're scoping to this chapter)
      new_path = Path("slides") / new_folder / stem
    else:
      # flat path: slides/file.md OR unexpected -> place into new folder
      new_path = Path("slides") / new_folder / stem
    rewrites.append((f, new_path.as_posix()))
    s["file"] = new_path.as_posix()

  # Update chapter folder
  chap["folder"] = new_folder

  # Optionally rename folder on disk
  fs_action = None
  if not args.no_fs:
    if old_folder:
      old_dir = SLIDES_DIR / old_folder
      new_dir = SLIDES_DIR / new_folder
      if old_dir.exists() and not new_dir.exists():
        fs_action = (old_dir, new_dir)
      # If it doesn't exist, we won't error; user may have moved manually.

  if args.dry_run:
    print(f"Chapter: {args.chapter}")
    print(f"Set folder: {chap.get('folder')} (old inferred: {old_folder})")
    print("Rewrite paths:")
    for a,b in rewrites[:50]:
      print(f"  {a} -> {b}")
    if fs_action:
      print(f"Would rename directory: {fs_action[0]} -> {fs_action[1]}")
    return

  if fs_action:
    fs_action[0].rename(fs_action[1])

  save_data(data)
  print(f"Updated chapter folder and rewrote {len(rewrites)} slide paths.")

if __name__ == "__main__":
  main()

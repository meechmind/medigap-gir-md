# Medigap GIR Deck (Markdown + Frontmatter)

## Goal
- Easy editing (one file per slide)
- No renumbering (slide numbers are computed dynamically from order)
- Single source of truth (only chapters list slide files)
- Still supports advanced custom layouts (raw HTML inside Markdown)

## Structure
- `index.html` — page shell
- `stylesheet.css` — styling (preserved from the original deck)
- `app.js` — loads `data.json`, loads slide files, renders nav + slides, wires up navigation
- `data.json` — ONLY chapters + ordered slide file references
- `slides/*.md` — slide content (Markdown + optional HTML) with frontmatter metadata

## Slide frontmatter
Each slide begins with:

---
id: s000
label: Sidebar label
title: Slide title
hidden: false (set to true to hide)
classes:
  - optional-class
---

Markdown content here...
(You can include raw HTML blocks anywhere.)

## Scripts
###  Creates a new slide (and chapter if applicable) - `scripts/new_slide.py`:
- Auto-creates new a chapter if it doesn't exist (`--chapter-title` sets its title)
- Creates a new slide inside a chapter folder under `slides/` (default)
- Updates data.json chapter id (if applicable) and filepaths

Examples:

Add a slide to an existing chapter, after another slide
`python scripts/new_slide.py --id objectives --label "Learning Objectives" --chapter welcome --after title` 
- Omit `--after ..` to have it append to the end

Auto-create a chapter and insert it after an existing chapter
`python scripts/new_slide.py --id new-slide --label "New Topic" --chapter new-chapter --chapter-title "New Chapter"`
- Add `--chapter-after` and the chapter name to insert it after a chapter rather than the end

### Rename
#### Rename a slide - `scripts/sync_slide_ids.py`
- Change the frontmatter `id` in the `.md` file.
- Renames the file to match the `id`, updates the `data.json` filepaths
- Run: `python scripts/sync_slide_ids.py`

#### Rename a chapter - `scripts/rename_chapter.py`
- Renames id in `data.json` + rewrites paths in `data.json` + renames folder on disk

Example
`python scripts/rename_chapter_id.py --old welcome --new introduction --update-folder`

### Move
### Move a slide to a different chapter - `move_slide.py`
- Moves the file to a different folder in `slides` and moves it in `data.json`
- To move a slide within a chapter, just move it in `data.json`
- Use `--after` and `--before` and the slide name to insert before/after
- Use `--no-fs` if you moved the file manually - this just updates data.json

Examples
`python scripts/move_slide.py --id timeline --from gir --to md-rules --after eligibility`

### Move a chapter - `move_chapter.py`
- Use this to change the order of a chapter
- automatically updates `data.json`
- Use `--after`, `--before`, `to-start`, `to-end` and the file name to dictate where the chapter gets inserted

Example
`python scripts/move_chapter.py --chapter appendix --after gir`

### Before pushing to Github
#### Check the manifest - `scripts/verify_manifest.py`
Run: `python scripts/verify_manifest.py`
- confirm every data.json slide file exists
- confirm every slide has a frontmatter id
- confirm slide id matches filename stem (so sync_slide_ids.py won’t surprise you)
- confirm no duplicate slide IDs across the deck
- confirm chapter.id == chapter.folderids, file names, folder names, etc. match
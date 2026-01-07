// app.js
// Markdown slide deck w/ optional frontmatter.
// data.json contains ONLY chapters + ordered slide file references (single source of truth).
// Each slide file provides id/label/title/classes/hidden via frontmatter.
// Raw HTML inside Markdown is supported (so you can go beyond Markdown when needed).
//
// Works on GitHub Pages (static hosting).

async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path} (${res.status})`);
  return res.json();
}

async function loadText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path} (${res.status})`);
  return res.text();
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("data-")) node.setAttribute(k, v);
    else node.setAttribute(k, v);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function validateManifest(data) {
  assert(data && typeof data === "object", "data.json must be an object");
  assert(Array.isArray(data.chapters), "data.json: chapters must be an array");
  for (const ch of data.chapters) {
    assert(typeof ch.id === "string" && ch.id, "chapter.id is required");
    assert(typeof ch.title === "string", `chapter ${ch.id} needs title`);
    assert(Array.isArray(ch.slides), `chapter ${ch.id} slides must be an array`);
    for (const s of ch.slides) {
      assert(typeof s.file === "string" && s.file, `chapter ${ch.id} slide needs file`);
    }
  }
}

// Very small YAML-ish frontmatter parser.
// Supports:
// ---
// id: my-slide
// label: Sidebar label
// title: Slide title
// hidden: true/false
// classes:
//   - foo
//   - bar
// ---
function parseFrontmatter(text, fallbackIdFromFilename = null) {
  const out = {
    id: fallbackIdFromFilename || null,
    label: null,
    title: null,
    hidden: false,
    classes: [],
    body: text,
  };

  if (!text.startsWith("---\n")) return out;

  const end = text.indexOf("\n---\n", 4);
  if (end === -1) return out;

  const fmBlock = text.slice(4, end).trimEnd();
  const body = text.slice(end + 5); // after \n---\n
  out.body = body;

  const lines = fmBlock.split(/\r?\n/);
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) { i++; continue; }

    if (line === "classes:" || line.startsWith("classes:")) {
      // Handle either "classes:" followed by "- item" lines
      // or "classes: [a, b]" (we'll do basic bracket parsing)
      if (line.includes("[") && line.includes("]")) {
        const inside = line.slice(line.indexOf("[") + 1, line.lastIndexOf("]"));
        out.classes = inside.split(",").map(s => s.trim()).filter(Boolean);
        i++;
        continue;
      }

      i++;
      const cls = [];
      while (i < lines.length) {
        const l = lines[i];
        const m = l.match(/^\s*-\s*(.+)\s*$/);
        if (!m) break;
        cls.push(m[1]);
        i++;
      }
      out.classes = cls;
      continue;
    }

    const kv = line.match(/^([A-Za-z0-9_-]+)\s*:\s*(.*)$/);
    if (kv) {
      const key = kv[1];
      let val = kv[2] ?? "";
      // Strip surrounding quotes if present
      val = val.replace(/^["'](.*)["']$/, "$1").trim();

      if (key === "id" && val) out.id = val;
      else if (key === "label") out.label = val;
      else if (key === "title") out.title = val;
      else if (key === "hidden") out.hidden = (val.toLowerCase() === "true");
    }

    i++;
  }

  return out;
}

// Markdown -> HTML
function mdToHtml(md) {
  if (!window.marked || typeof window.marked.parse !== "function") {
    throw new Error("Markdown renderer not loaded. Ensure marked is included in index.html.");
  }
  // marked preserves raw HTML blocks by default (good for advanced layouts).
  return window.marked.parse(md);
}

function filenameToId(path) {
  // slides/foo-bar.md -> foo-bar
  const last = path.split("/").pop() || path;
  return last.replace(/\.(md|markdown)$/i, "");
}

function renderSidebar(sidebarEl, data, visibleSlidesById, chapterToVisibleIds) {
  sidebarEl.innerHTML = "";
  sidebarEl.appendChild(el("div", { class: "nav-title", html: data.meta?.navTitle || "Presentation" }));

  for (const chapter of data.chapters) {
    const ids = chapterToVisibleIds.get(chapter.id) || [];
    if (ids.length === 0) continue;

    const header = el("div", { class: "chapter-header", "data-chapter": chapter.id });
    header.appendChild(el("span", { class: "arrow", html: "▶" }));
    header.appendChild(el("span", { html: chapter.title }));

    const slidesWrap = el("div", { class: "chapter-slides", "data-chapter": chapter.id });

    for (const id of ids) {
      const s = visibleSlidesById.get(id);
      const label = s?.label || s?.title || id;
      slidesWrap.appendChild(el("div", { class: "slide-link", "data-slide-id": id, html: label }));
    }

    sidebarEl.appendChild(el("div", { class: "nav-chapter" }, [header, slidesWrap]));
  }
}

function renderSlides(slidesRootEl, visibleSlidesOrdered) {
  slidesRootEl.innerHTML = "";
  for (let i = 0; i < visibleSlidesOrdered.length; i++) {
    const s = visibleSlidesOrdered[i];
    const classes = ["slide", ...(s.classes || [])];
    if (i === 0) classes.push("active");

    slidesRootEl.appendChild(
      el("section", {
        class: classes.join(" "),
        "data-index": String(i),
        "data-id": s.id,
        html: s.html,
      })
    );
  }
}

function wireUpNavigation(visibleSlidesOrdered) {
  let currentIndex = 0;

  const slides = Array.from(document.querySelectorAll(".slide"));
  const total = slides.length;
  const slideLinks = Array.from(document.querySelectorAll("#sidebar .slide-link"));
  const chapterHeaders = Array.from(document.querySelectorAll(".chapter-header"));

  const idToIndex = new Map(visibleSlidesOrdered.map((s, i) => [s.id, i]));

  document.getElementById("total-slides").textContent = total;

  function expandChapterForLink(link) {
    const chapterSlides = link.closest(".chapter-slides");
    if (!chapterSlides) return;
    const chapterId = chapterSlides.dataset.chapter;
    const chapterHeader = document.querySelector(`.chapter-header[data-chapter="${chapterId}"]`);

    document.querySelectorAll(".chapter-slides").forEach((cs) => cs.classList.remove("expanded"));
    document.querySelectorAll(".chapter-header").forEach((ch) => ch.classList.remove("expanded"));

    chapterSlides.classList.add("expanded");
    if (chapterHeader) chapterHeader.classList.add("expanded");
  }

  function show(index) {
    if (index < 0 || index >= total) return;

    slides.forEach((s) => s.classList.remove("active"));
    slides[index].classList.add("active");
    currentIndex = index;

    document.getElementById("current-slide").textContent = index + 1;

    slideLinks.forEach((l) => l.classList.remove("active"));
    const activeId = visibleSlidesOrdered[index]?.id;
    const activeLink = document.querySelector(`#sidebar .slide-link[data-slide-id="${activeId}"]`);
    if (activeLink) {
      activeLink.classList.add("active");
      expandChapterForLink(activeLink);
      activeLink.scrollIntoView({ block: "nearest" });
    }
  }

  function showById(id) {
    const idx = idToIndex.get(id);
    if (idx == null) return;
    show(idx);
  }

  document.addEventListener("keydown", (e) => {
    const key = e.key;
    if (key === "ArrowRight" || key === "PageDown" || key === " ") {
      e.preventDefault();
      show(currentIndex + 1);
    } else if (key === "ArrowLeft" || key === "PageUp") {
      e.preventDefault();
      show(currentIndex - 1);
    } else if (key === "Home") {
      e.preventDefault();
      show(0);
    } else if (key === "End") {
      e.preventDefault();
      show(total - 1);
    }
  });

  document.addEventListener("click", (e) => {
    const link = e.target.closest('[data-slide-id]');
    if (!link) return;
    e.preventDefault();
    showById(link.dataset.slideId);
  });

  chapterHeaders.forEach((header) => {
    header.addEventListener("click", () => {
      const chapterId = header.dataset.chapter;
      const chapterSlides = document.querySelector(`.chapter-slides[data-chapter="${chapterId}"]`);
      if (!chapterSlides) return;

      const isExpanded = chapterSlides.classList.contains("expanded");
      if (!isExpanded) {
        document.querySelectorAll(".chapter-slides").forEach((cs) => cs.classList.remove("expanded"));
        document.querySelectorAll(".chapter-header").forEach((ch) => ch.classList.remove("expanded"));
        chapterSlides.classList.add("expanded");
        header.classList.add("expanded");
      } else {
        chapterSlides.classList.remove("expanded");
        header.classList.remove("expanded");
      }
    });
  });

  const firstChapterHeader = document.querySelector(".chapter-header");
  if (firstChapterHeader) {
    const cid = firstChapterHeader.dataset.chapter;
    const cs = document.querySelector(`.chapter-slides[data-chapter="${cid}"]`);
    if (cs) {
      firstChapterHeader.classList.add("expanded");
      cs.classList.add("expanded");
    }
  }

  show(0);
}

async function init() {
  const data = await loadJSON("./data.json");
  validateManifest(data);

  // 1) Flatten slide files in chapter order (single source of truth)
  const flat = [];
  for (const ch of data.chapters) {
    for (const s of ch.slides) {
      flat.push({ chapterId: ch.id, file: s.file });
    }
  }

  // 2) Load slides (frontmatter + HTML)
  const slides = [];
  for (const item of flat) {
    const raw = await loadText(item.file);
    const fallbackId = filenameToId(item.file);
    const fm = parseFrontmatter(raw, fallbackId);

    // Convert body markdown to HTML
    const html = mdToHtml(fm.body);

    slides.push({
      chapterId: item.chapterId,
      id: fm.id || fallbackId,
      label: fm.label || null,
      title: fm.title || null,
      hidden: !!fm.hidden,
      classes: Array.isArray(fm.classes) ? fm.classes : [],
      html,
    });
  }

  // 3) Validate uniqueness
  const ids = new Set();
  for (const s of slides) {
    if (ids.has(s.id)) throw new Error(`Duplicate slide id detected: ${s.id}`);
    ids.add(s.id);
  }

  // 4) Filter hidden
  const visibleSlidesOrdered = slides.filter((s) => !s.hidden);

  // Build lookups for sidebar rendering
  const visibleSlidesById = new Map(visibleSlidesOrdered.map((s) => [s.id, s]));
  const chapterToVisibleIds = new Map();
  for (const ch of data.chapters) chapterToVisibleIds.set(ch.id, []);
  for (const s of visibleSlidesOrdered) {
    chapterToVisibleIds.get(s.chapterId)?.push(s.id);
  }

  // 5) Render + wire up
  renderSidebar(document.getElementById("sidebar"), data, visibleSlidesById, chapterToVisibleIds);
  renderSlides(document.getElementById("slides-root"), visibleSlidesOrdered);
  wireUpNavigation(visibleSlidesOrdered);
}

init().catch((err) => {
  console.error(err);
  const main = document.querySelector(".main-content");
  const pre = document.createElement("pre");
  pre.style.whiteSpace = "pre-wrap";
  pre.style.padding = "1rem";
  const msg = [err.message, err.stack].filter(Boolean).join("\n\n");
  pre.textContent = `Error loading presentation:\n\n${msg || String(err)}`;
  main.prepend(pre);
});

// Library: Bible translations, commentaries, dictionaries and other books.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, icon, modal, segmented, toast, toggle } from "../ui.js";

const GROUPS = [
  ["scripture", "Bible translations", "Scripture text, read verbatim."],
  ["commentary", "Commentaries", "Explanations of Scripture written by people. Not Scripture."],
  ["dictionary", "Bible dictionaries", "Articles about people, places and words. Not Scripture."],
  ["reference", "Other reference books", "Any other related books you own or have the right to use. Not Scripture."],
];

export async function renderLibrary(root, params = {}) {
  const searchBox = el("input", { class: "input", placeholder: "Search your whole library…", value: params.search || "", "aria-label": "Search library" });
  const results = el("div");
  const groups = el("div", { style: { marginTop: "22px" } });
  root.append(
    el("div", { class: "spread" },
      el("div", {}, el("div", { class: "eyebrow" }, "Library"), el("h1", {}, "Your books")),
      el("button", { class: "btn primary", onclick: () => openImport(draw) }, icon("plus", 16), "Add a Bible or book")),
    el("div", { class: "card", style: { marginTop: "16px" } }, el("div", { class: "row" }, searchBox,
      el("button", { class: "btn", onclick: () => search() }, icon("search", 16), "Search")), results),
    groups,
  );
  searchBox.addEventListener("keydown", (e) => { if (e.key === "Enter") search(); });

  async function search() {
    const q = searchBox.value.trim();
    if (!q) { results.replaceChildren(); return; }
    results.replaceChildren(el("div", { class: "empty" }, el("span", { class: "spinner" })));
    try { showResults(await api.get(`/api/search?${api.qs({ q })}`)); } catch (e) { results.replaceChildren(el("div", { class: "notice err" }, e.message)); }
  }

  function showResults(r) {
    results.replaceChildren(
      el("h3", { style: { marginTop: "16px" } }, `Scripture (${r.scripture.length})`),
      ...(r.scripture.length ? r.scripture.map((h) => el("div", { class: "source scripture", style: { marginTop: "8px", cursor: "pointer" }, onclick: () => window.bnNavigate("read", { ref: h.label }) },
        el("div", { class: "src-head" }, el("span", { class: "chip scripture" }, "Scripture"), el("b", {}, `${h.label} (${h.translation})`)),
        el("div", { class: "src-text" }, h.text))) : [el("p", { class: "muted small" }, "No verses matched.")]),
      el("h3", { style: { marginTop: "16px" } }, `Reference books (${r.reference.length})`),
      ...(r.reference.length ? r.reference.map((s) => el("div", { class: "source ref", style: { marginTop: "8px" } },
        el("div", { class: "src-head" }, el("span", { class: "chip reference" }, `${s.kind_label} · not Scripture`), el("b", {}, s.title), el("span", { class: "small muted" }, s.label)),
        el("div", { class: "src-text" }, s.text.length > 500 ? `${s.text.slice(0, 500)}…` : s.text))) : [el("p", { class: "muted small" }, "No reference entries matched.")]),
    );
  }

  async function draw() {
    const r = await store.refreshSources();
    groups.replaceChildren();
    for (const [kind, title, sub] of GROUPS) {
      const items = r.sources.filter((s) => s.kind === kind);
      if (!items.length && kind !== "scripture" && kind !== "commentary") continue;
      const cards = el("div", { class: "lib-cards" });
      for (const s of items) cards.append(sourceCard(s, draw));
      if (!items.length) cards.append(el("div", { class: "card flat small muted" }, kind === "commentary"
        ? "No commentaries yet. Import a public-domain commentary (for example as text, PDF, EPUB, or a verse-keyed CSV) with “Add a Bible or book”."
        : "No Bible yet."));
      groups.append(el("section", { class: "lib-group" },
        el("div", { class: "row" }, el("h2", {}, title), kind === "scripture" ? el("span", { class: "badge accent" }, "Scripture") : el("span", { class: "badge notscripture" }, "Not Scripture")),
        el("p", { class: "muted small", style: { margin: "4px 0 0" } }, sub), cards));
    }
    const missing = r.starter.filter((x) => !x.installed);
    if (missing.length) {
      groups.append(el("div", { class: "card flat" }, el("h3", {}, "Bundled public-domain texts"),
        el("p", { class: "small muted" }, "These came with the app and can be re-added at any time (no internet needed)."),
        el("div", { class: "row wrap" }, ...missing.map((m) => el("button", { class: "btn small", onclick: async () => {
          await api.post("/api/starter/install", { keys: [m.key] }); toast(`${m.title} added.`); draw();
        } }, icon("plus", 14), `${m.title} (${m.license})`)))));
    }
  }

  if (params.results) showResults(params.results);
  await draw();
}

function sourceCard(s, redraw) {
  const isDefault = s.kind === "scripture" && store.translationId() === s.id;
  const card = el("div", { class: "card lib-card" },
    el("div", { class: "spread" },
      el("div", {}, el("h3", {}, s.title), el("div", { class: "small muted" }, [s.abbreviation, s.edition].filter(Boolean).join(" · "))),
      toggle(s.enabled, async (v) => { await api.patch(`/api/sources/${s.id}`, { enabled: v }); toast(v ? "Enabled for search and answers." : "Disabled: not used for search or answers."); redraw(); })),
    el("div", { class: "row wrap" },
      el("span", { class: s.kind === "scripture" ? "chip scripture" : "chip reference" }, s.kind_label),
      el("span", { class: "chip" }, s.kind === "scripture" ? `${s.item_count.toLocaleString()} verses` : `${s.item_count.toLocaleString()} entries`),
      s.builtin ? el("span", { class: "chip" }, "Bundled") : null,
      isDefault ? el("span", { class: "chip dark" }, "Default") : null),
    el("div", { class: "lic" }, el("b", {}, "License: "), s.license || "not specified"),
    s.attribution ? el("div", { class: "lic" }, s.attribution) : null,
    s.source_url ? el("div", { class: "lic" }, `Source: ${s.source_url}`) : null,
    s.notes ? el("div", { class: "lic" }, s.notes) : null,
    el("div", { class: "row wrap", style: { marginTop: "auto" } },
      s.kind === "scripture" && !isDefault ? el("button", { class: "btn small", onclick: async () => { await store.saveSettings({ default_translation: String(s.id) }); redraw(); } }, "Make default") : null,
      s.kind === "scripture" ? el("button", { class: "btn small", onclick: () => { store.saveSettings({ default_translation: String(s.id) }); window.bnNavigate("read"); } }, icon("book", 14), "Read") : null,
      el("button", { class: "btn small", onclick: () => editSource(s, redraw) }, "Edit details"),
      el("button", { class: "btn small ghost danger", onclick: async () => {
        if (!confirm(`Remove “${s.title}” from your library? The original file on your disk is not touched.`)) return;
        await api.del(`/api/sources/${s.id}`); toast("Removed."); redraw();
      } }, icon("trash", 14), "Remove")),
  );
  return card;
}

function metaFields(values, licenses, { withKind = false } = {}) {
  const f = {};
  const field = (key, label, attrs = {}) => {
    f[key] = el("input", { class: "input", value: values[key] || "", ...attrs });
    return el("label", { class: "field" }, el("span", {}, label), f[key]);
  };
  const lic = el("select", { class: "input" }, ...licenses.map((l) => el("option", { value: l }, l)));
  lic.value = licenses.includes(values.license) ? values.license : (values.license ? "Other (see notes)" : "Unknown");
  f.license = lic;
  const node = el("div", { class: "grid", style: { gridTemplateColumns: "1fr 1fr" } },
    field("title", "Title *", { placeholder: "e.g. World English Bible" }),
    field("abbreviation", "Abbreviation", { placeholder: "e.g. WEB" }),
    field("edition", "Translation / edition", { placeholder: "e.g. 2020 edition" }),
    el("label", { class: "field" }, el("span", {}, "License"), lic),
    field("attribution", "Attribution / copyright notice"),
    field("source_url", "Where it came from (URL or publisher)"),
    field("language", "Language code", { placeholder: "en" }),
    field("notes", "Notes"));
  return { node, f, withKind };
}

async function editSource(s, redraw) {
  const { licenses } = await api.get("/api/sources");
  const { node, f } = metaFields(s, licenses);
  const save = el("button", { class: "btn primary" }, "Save");
  const m = modal(el("div", { class: "stack" }, el("h2", {}, "Edit details"), node, save), { wide: true });
  save.onclick = async () => {
    const body = Object.fromEntries(Object.entries(f).map(([k, n]) => [k, n.value]));
    try { await api.patch(`/api/sources/${s.id}`, body); m.close(); redraw(); } catch (e) { toast(e.message, "err"); }
  };
}

export async function openImport(onDone) {
  const { licenses, kinds } = await api.get("/api/sources");
  let kind = "scripture";
  const file = el("input", { type: "file", class: "input", "aria-label": "File to import",
    accept: ".json,.gz,.csv,.tsv,.usfm,.sfm,.zip,.xml,.osis,.txt,.md,.pdf,.epub,.html,.htm" });
  const { node, f } = metaFields({ license: "Unknown", language: "en" }, licenses);
  const rights = el("input", { type: "checkbox", id: "rights" });
  const formats = el("div", { class: "small muted" });
  const setFormats = () => {
    formats.textContent = kind === "scripture"
      ? "Bible formats: USFM (.usfm or a .zip of USFM files, e.g. from eBible.org), OSIS or Zefania XML, JSON, CSV/TSV (book, chapter, verse, text), or verse-per-line text (“Gen 1:1 In the beginning…”)."
      : "Book formats: PDF (page numbers kept), EPUB, HTML, text or Markdown (headings become sections), or JSON/CSV entries — dictionaries {term, text}, verse-keyed commentary {book, chapter, verse_start, verse_end, text}.";
  };
  setFormats();
  const go = el("button", { class: "btn primary big" }, icon("upload", 16), "Import");
  const status = el("div");
  const m = modal(el("div", { class: "stack" },
    el("div", { class: "eyebrow" }, "Add to your library"),
    el("h2", {}, "Import a Bible or related book"),
    el("label", { class: "field" }, el("span", {}, "What is it?"),
      segmented([["scripture", "Bible (Scripture)"], ["commentary", "Commentary"], ["dictionary", "Bible dictionary"], ["reference", "Other book"]].filter(([k]) => kinds.includes(k)), kind,
        (v) => { kind = v; setFormats(); })),
    el("label", { class: "field" }, el("span", {}, "File"), file), formats,
    node,
    el("label", { class: "row small" }, rights, el("span", {}, "I have the right to use this content (it is public domain, openly licensed, or licensed to me).")),
    go, status), { wide: true });

  go.onclick = async () => {
    const fl = file.files[0];
    if (!fl) { toast("Choose a file first.", "err"); return; }
    if (!rights.checked) { toast("Please confirm you have the right to use this content.", "err"); return; }
    const meta = Object.fromEntries(Object.entries(f).map(([k, n]) => [k, n.value]));
    go.disabled = true;
    status.replaceChildren(el("div", { class: "row" }, el("span", { class: "spinner" }), `Importing ${fl.name}…`));
    try {
      const buf = await fl.arrayBuffer();
      const res = await api.raw("POST", `/api/sources/import?${api.qs({ ...meta, kind, filename: fl.name, rights_confirmed: "1" })}`, buf,
        { "Content-Type": "application/octet-stream" }).then((x) => x.json());
      const what = res.verses ? `${res.verses.toLocaleString()} verses in ${res.books} books` : `${res.entries.toLocaleString()} entries`;
      toast(`Imported “${res.source.title}”: ${what}.`);
      if (res.warning) toast(res.warning);
      m.close();
      onDone && onDone(res);
    } catch (e) {
      status.replaceChildren(el("div", { class: "notice err" }, icon("info"), e.message));
      go.disabled = false;
    }
  };
}

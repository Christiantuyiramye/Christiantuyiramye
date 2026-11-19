// Read Scripture: verbatim text with translation + verse references, played verse by verse.
import { api } from "../api.js";
import { player, scripturePlaylist } from "../player.js";
import { store } from "../store.js";
import { openTheater } from "../story.js";
import { el, icon, segmented, toast, toggle } from "../ui.js";

export async function renderRead(root, params = {}) {
  let sourceId = store.translationId();
  if (!sourceId) {
    root.append(el("div", { class: "card empty" }, el("h2", {}, "No Bible in your library"),
      el("p", {}, "Add a Bible translation to start reading."), el("button", { class: "btn primary", onclick: () => window.bnNavigate("library") }, "Open Library")));
    return;
  }
  let ref = params.ref || store.settings.last_passage || "John 1";
  let passage = null;
  let books = [];
  let testament = "OT";
  const viewStart = Date.now();

  const picker = el("div", { class: "picker" });
  const textCard = el("div", { class: "card scripture-card" });
  const study = el("aside", { class: "card flat study", "aria-label": "Study notes (not Scripture)" });
  root.append(el("div", { class: "reader" }, picker, textCard, study));

  const offs = [
    store.on("player:item", ({ playlist, index }) => highlight(playlist, index)),
    store.on("player:autocontinue", (p) => { passage = p; ref = p.reference; drawText(); drawPicker(); drawStudy(); }),
  ];

  async function loadBooks() {
    const r = await api.get(`/api/books?${api.qs({ source_id: sourceId })}`);
    books = r.books;
  }

  async function load(newRef) {
    try {
      passage = await api.get(`/api/passage?${api.qs({ ref: newRef, source_id: sourceId })}`);
    } catch (e) {
      toast(e.message, "err");
      if (!passage) { passage = await api.get(`/api/passage?${api.qs({ ref: "John 1", source_id: sourceId })}`); }
    }
    ref = passage.reference;
    testament = passage.book <= 39 ? "OT" : "NT";
    store.saveSettings({ last_passage: ref }).catch(() => {});
    drawPicker(); drawText(); drawStudy();
  }

  function drawPicker() {
    const currentBook = passage ? passage.book : 43;
    const list = el("div", { class: "books" });
    for (const b of books.filter((x) => x.testament === testament)) {
      list.append(el("button", { class: b.number === currentBook ? "on" : "", onclick: () => load(`${b.name} 1`) }, b.name));
    }
    const nCh = (books.find((b) => b.number === currentBook) || {}).chapters || 0;
    const chapters = el("div", { class: "chapters", "aria-label": "Chapters" });
    for (let c = 1; c <= nCh; c++) {
      chapters.append(el("button", { class: passage && passage.chapter === c && passage.whole_chapter ? "on" : "",
        onclick: () => load(`${passage.book_name} ${c}`) }, String(c)));
    }
    picker.replaceChildren(
      segmented([["OT", "Old Testament"], ["NT", "New Testament"]], testament, (v) => { testament = v; drawPicker(); }),
      el("div", { class: "card flat", style: { padding: "8px", overflow: "auto", flex: "1 1 50%" } }, list),
      el("div", { class: "card flat", style: { padding: "12px", overflow: "auto" } },
        el("div", { class: "eyebrow", style: { marginBottom: "8px" } }, `${passage ? passage.book_name : ""} · chapters`), chapters),
    );
    const on = list.querySelector(".on");
    if (on) on.scrollIntoView({ block: "center" });
  }

  function drawText() {
    const src = passage.source;
    const bibles = store.bibles();
    const sel = el("select", { class: "input", style: { width: "auto" }, "aria-label": "Translation" },
      ...bibles.map((b) => el("option", { value: b.id }, `${b.abbreviation || ""} — ${b.title}`)));
    sel.value = String(src.id);
    sel.onchange = async () => {
      sourceId = Number(sel.value);
      store.saveSettings({ default_translation: String(sourceId) });
      await loadBooks();
      load(ref);
    };
    const lookup = el("input", { class: "input", placeholder: "Go to… e.g. Psalm 23", "aria-label": "Passage lookup", style: { maxWidth: "200px" } });
    lookup.addEventListener("keydown", (e) => { if (e.key === "Enter" && lookup.value.trim()) load(lookup.value.trim()); });

    const playAll = el("button", { class: "btn primary" }, icon("play", 16), passage.whole_chapter ? "Play chapter" : "Play passage");
    playAll.onclick = () => startPlayback(0);
    const auto = el("div", { class: "row small", title: "When a chapter ends, keep reading the next one (Genesis to Revelation)." },
      toggle(store.settings.auto_continue, (v) => store.saveSettings({ auto_continue: v })), el("span", {}, "Auto mode"));

    const text = el("div", { class: "scripture-text", lang: src.language || "en" });
    let lastChapter = null;
    for (const v of passage.verses) {
      if (lastChapter !== null && v.chapter !== lastChapter) text.append(el("h3", { style: { margin: "18px 0 6px" } }, `Chapter ${v.chapter}`));
      lastChapter = v.chapter;
      const span = el("span", { class: "verse", dataset: { key: `${v.chapter}:${v.verse}` }, title: "Play from this verse", tabindex: "0" },
        el("sup", {}, String(v.verse)), v.text, " ");
      span.onclick = () => startPlayback(passage.verses.indexOf(v));
      span.onkeydown = (e) => { if (e.key === "Enter") span.click(); };
      text.append(span);
    }
    textCard.replaceChildren(
      el("div", { class: "scripture-head" },
        el("div", {},
          el("div", { class: "row" }, el("span", { class: "badge accent" }, "Scripture"), el("span", { class: "small muted", style: { whiteSpace: "nowrap" } }, "Verbatim text")),
          el("h1", { style: { marginTop: "8px" } }, passage.reference),
          el("div", { class: "translation-line" }, `${src.title}${src.abbreviation ? ` (${src.abbreviation})` : ""}${src.edition ? ` · ${src.edition}` : ""}`),
          el("div", { class: "translation-line" }, `License: ${src.license || "not specified"}`)),
        el("div", { style: { width: "230px", flex: "none" } }, sel)),
      el("div", { class: "row wrap", style: { marginBottom: "18px" } }, playAll,
        el("button", { class: "btn", onclick: () => { if (!isLoaded()) startPlayback(0, false); openTheater(); } }, icon("film", 16), "Story view"),
        el("button", { class: "btn", onclick: () => window.bnNavigate("story", { ref: passage.reference }) }, icon("sparkle", 16), "Retell"),
        auto, lookup),
      text,
      el("div", { class: "chapter-nav" },
        passage.prev ? el("button", { class: "btn", onclick: () => load(passage.prev) }, icon("chevronL"), passage.prev) : el("span"),
        passage.next ? el("button", { class: "btn", onclick: () => load(passage.next) }, passage.next, icon("chevronR")) : el("span")),
    );
    if (isLoaded()) highlight(player.playlist, player.index);
  }

  function drawStudy() {
    const items = [];
    for (const n of passage.commentary) items.push(entry(n.heading || `on ${n.verse_start || ""}`, n.text, n.title, n.kind, n.location));
    for (const d of passage.dictionary) items.push(entry(d.heading, d.text, d.title, d.kind, d.location));
    study.replaceChildren(
      el("div", { class: "spread" }, el("h3", {}, "Study notes"), el("span", { class: "badge notscripture" }, "Not Scripture")),
      el("p", { class: "small muted", style: { margin: "6px 0 10px" } }, "From commentaries and dictionaries in your library. These are human-written explanations, not Bible text."),
      ...(items.length ? items : [el("div", { class: "small muted" }, "No notes for this passage in your reference books.")]),
    );
  }

  function entry(heading, text, title, kind, location) {
    const e = el("div", { class: "entry" },
      el("h4", {}, heading),
      el("div", { class: "row small muted", style: { gap: "6px", marginBottom: "4px" } }, el("span", { class: "chip reference" }, kind === "dictionary" ? "Dictionary" : kind === "commentary" ? "Commentary" : "Reference"), `${title}${location ? ` · ${location}` : ""}`),
      el("p", {}, text));
    e.onclick = () => e.classList.toggle("open");
    return e;
  }

  function isLoaded() { return player.playlist && player.playlist.id === `scripture:${passage.source.id}:${passage.reference}`; }

  function startPlayback(verseIndex, autoplay = true) {
    const pl = scripturePlaylist(passage, { announce: store.settings.announce_passage && verseIndex === 0 });
    const offset = pl.items[0] && pl.items[0].intro ? 1 : 0;
    if (isLoaded() && autoplay) { player.jumpTo(verseIndex + (player.playlist.items[0].intro ? 1 : 0)); if (!player.playing) player.play(); return; }
    player.load(pl, { start: verseIndex === 0 ? 0 : verseIndex + offset, autoplay });
  }

  function highlight(playlist, index) {
    textCard.querySelectorAll(".verse.current").forEach((n) => n.classList.remove("current"));
    if (!passage || !playlist || playlist.id !== `scripture:${passage.source.id}:${passage.reference}`) return;
    const item = playlist.items[index];
    if (!item || item.intro) return;
    const node = textCard.querySelector(`.verse[data-key="${item.key}"]`);
    if (node) {
      node.classList.add("current");
      if (store.settings.auto_scroll) node.scrollIntoView({ block: "center", behavior: store.settings.reduce_motion ? "auto" : "smooth" });
    }
  }

  await loadBooks();
  await load(ref);

  return () => {
    offs.forEach((f) => f());
    const secs = (Date.now() - viewStart) / 1000;
    if (passage && secs > 30) {
      api.post("/api/history", { book: passage.book, chapter: passage.chapter, source_id: passage.source.id, mode: "read", seconds: Math.round(secs), completed: false }).catch(() => {});
    }
  };
}

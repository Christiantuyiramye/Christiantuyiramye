// Retell a Bible passage: short faithful retelling, coloured story animation, narration.
import { api } from "../api.js";
import { player } from "../player.js";
import { store } from "../store.js";
import { StoryScene, bindSceneToPlayer, openTheater } from "../story.js";
import { el, icon, toast } from "../ui.js";

export async function renderStory(root, params = {}) {
  let sourceId = store.translationId();
  const input = el("input", { class: "input", placeholder: "A passage (Genesis 22:1-19) or an event (Jesus calms the storm)", "aria-label": "Passage or event", value: params.ref || "" });
  const sel = el("select", { class: "input", style: { width: "auto" }, "aria-label": "Translation" },
    ...store.bibles().map((b) => el("option", { value: b.id }, b.abbreviation || b.title)));
  sel.value = String(sourceId || "");
  sel.onchange = () => { sourceId = Number(sel.value); };
  const go = el("button", { class: "btn primary", id: "retell-go" }, icon("sparkle", 16), "Retell");
  const out = el("div", { style: { marginTop: "18px" } });
  root.append(
    el("div", { class: "spread" },
      el("div", {}, el("div", { class: "eyebrow" }, "Retell a Bible passage"), el("h1", {}, "Hear the story, simply told")),
      el("span", { class: "badge notscripture", title: "Retellings are summaries. Read Scripture for the exact text." }, "Retelling · not Scripture text")),
    el("p", { class: "muted", style: { maxWidth: "720px" } },
      "A concise narration of only the events in the passage — no added dialogue, motives, scenes, characters or morals. Every sentence is checked against the verses it cites."),
    el("div", { class: "card", style: { marginTop: "14px" } },
      el("div", { class: "row" }, input, sel, go),
      el("div", { class: "row wrap small muted", style: { marginTop: "10px" } }, "Try:",
        ...["Genesis 22:1-14", "Mark 4:35-41", "Exodus 14:21-31", "Luke 15:11-32", "Ruth 1"].map((r) =>
          el("button", { class: "chip", onclick: () => { input.value = r; run(); } }, r)))),
    out,
  );
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
  go.onclick = run;
  let scene = null;
  let unbind = null;

  async function run() {
    const q = input.value.trim();
    if (!q) { input.focus(); return; }
    out.replaceChildren(el("div", { class: "card empty" }, el("span", { class: "spinner" }), el("p", {}, "Looking up the passage…")));
    try {
      const c = await api.get(`/api/retell/candidates?${api.qs({ q, source_id: sourceId })}`);
      if (c.reference) return retell(c.reference);
      if (!c.candidates.length) {
        out.replaceChildren(el("div", { class: "notice" }, icon("info"), "I couldn't find a passage about that in your library. Try different words or a reference like “Mark 4:35-41”."));
        return;
      }
      out.replaceChildren(el("div", { class: "card" },
        el("h3", {}, "Which passage do you mean?"),
        el("p", { class: "small muted" }, "Pick the passage to retell. You'll see its text first."),
        el("div", { class: "candidates", style: { marginTop: "10px" } }, ...c.candidates.map((x) =>
          el("button", { class: "candidate", onclick: () => { input.value = x.reference; retell(x.reference); } },
            el("div", { class: "row" }, el("b", {}, x.reference), x.origin === "model" ? el("span", { class: "chip", title: x.note }, "AI suggestion — check the text") : el("span", { class: "chip" }, "Search match")),
            el("div", { class: "snip" }, /^[“"]/.test(x.snippet) ? `${x.snippet} — ${x.snippet_ref}` : `“${x.snippet}” — ${x.snippet_ref}`))))));
    } catch (e) { out.replaceChildren(el("div", { class: "notice err" }, icon("info"), e.message)); }
  }

  async function retell(reference) {
    out.replaceChildren(el("div", { class: "card empty" }, el("span", { class: "spinner" }),
      el("p", {}, store.modelReady() ? "Writing a faithful retelling with the local AI model… (this can take a little while)" : "Preparing…")));
    let r;
    try { r = await api.post("/api/retell", { reference, source_id: sourceId }); } catch (e) {
      out.replaceChildren(el("div", { class: "notice err" }, icon("info"), e.message)); return;
    }
    show(r);
  }

  function show(r) {
    const condensed = r.mode === "condensed";
    const canvas = el("canvas", { "aria-label": "Animated story scene" });
    const stage = el("div", { class: "stage" }, canvas,
      el("div", { class: "stage-actions" },
        el("button", { class: "btn small", onclick: () => openTheater() }, icon("expand", 14), "Full screen"),
        el("button", { class: "btn small", onclick: () => openTheater() }, icon("record", 12), "Make a video")));
    if (unbind) unbind();
    if (scene) scene.stop();
    scene = new StoryScene(canvas);
    scene.reduceMotion = !!store.settings.reduce_motion;
    scene.setSegment({ text: "", label: r.reference, kindLabel: condensed ? "Exact verses" : "Retelling · not Scripture text", title: r.reference,
      motifText: r.verses.map((v) => v.text).join(" ") });
    if (store.settings.story_visuals !== false) scene.start();
    unbind = bindSceneToPlayer(scene);

    const byKey = Object.fromEntries(r.verses.map((v) => [`${v.chapter}:${v.verse}`, v]));
    const items = r.sentences.map((s, i) => ({
      key: `s${i}`, text: s.text, label: s.refs.join(", "), motifText: (s.verse_keys || []).map((k) => byKey[k]?.text || "").join(" ") || s.text,
    }));
    const playlist = { id: `retell:${r.source_id}:${r.reference}:${r.mode}`, kind: condensed ? "condensed" : "retell",
      title: `${r.reference} — ${condensed ? "key verses" : "retold"}`, subtitle: `${r.abbreviation || r.translation}${condensed ? "" : " · retelling"}`, items };
    const playBtn = el("button", { class: "btn primary" }, icon("play", 16), condensed ? "Listen to key verses" : "Listen to the retelling");
    playBtn.onclick = () => player.load(playlist, { autoplay: true });

    const list = el("div", { class: "story-sentences" });
    r.sentences.forEach((s, i) => {
      const row = el("div", { class: `story-sentence ${s.verbatim ? "verbatim" : ""}`, dataset: { i: String(i) }, title: "Play from here" },
        el("span", { class: "num" }, String(i + 1)),
        el("div", {}, el("div", { class: "txt" }, s.text), el("div", { class: "refs" }, ...s.refs.map((x) => el("span", { class: "chip scripture" }, x)))));
      row.onclick = () => { if (player.playlist && player.playlist.id === playlist.id) player.jumpTo(i); else player.load(playlist, { start: i }); if (!player.playing) player.play(); };
      list.append(row);
    });

    const notes = (r.notes || []).map((n) => el("div", { class: `notice ${condensed ? "warn" : ""}` }, icon("info"), n));
    const removed = (r.removed && r.removed.length) ? el("details", { class: "removed" },
      el("summary", {}, `Removed by the accuracy checks (${r.removed.length})`),
      el("ul", {}, ...r.removed.map((x) => el("li", {}, `“${x.text}” — ${x.reason}`)))) : null;
    const passage = el("details", { class: "card flat" },
      el("summary", { style: { cursor: "pointer", fontWeight: 600 } }, `Source passage: ${r.reference} (${r.abbreviation || r.translation})`),
      el("div", { class: "scripture-text", style: { fontSize: "16px", marginTop: "10px" } },
        ...r.verses.map((v) => el("span", { class: "verse" }, el("sup", {}, String(v.verse)), v.text, " "))),
      el("p", { class: "small muted" }, `${r.translation} · License: ${r.license || "not specified"}`));

    out.replaceChildren(el("div", { class: "story-layout" },
      el("div", {}, stage, el("p", { class: "small muted", style: { marginTop: "8px" } },
        "Decorative visuals: colours and shapes are picked from words in the passage (like “sea” or “night”); they don't depict people or events.")),
      el("div", { class: "card" },
        el("div", { class: "spread" },
          el("div", {}, el("span", { class: condensed ? "badge" : "badge notscripture" }, condensed ? "Condensed reading · exact verses" : "AI retelling · not Scripture text"),
            el("h2", { style: { marginTop: "8px" } }, r.reference)),
          el("button", { class: "btn small", onclick: () => window.bnNavigate("read", { ref: r.reference }) }, icon("book", 14), "Read it")),
        el("div", { class: "row wrap", style: { margin: "14px 0" } }, playBtn),
        ...notes, list, removed, el("div", { style: { marginTop: "14px" } }, passage))));

    const offItem = store.on("player:item", ({ playlist: pl, index }) => {
      list.querySelectorAll(".current").forEach((n) => n.classList.remove("current"));
      if (pl && pl.id === playlist.id) list.querySelector(`[data-i="${index}"]`)?.classList.add("current");
    });
    const prevUnbind = unbind;
    unbind = () => { prevUnbind(); offItem(); };
    if (!r.sentences.length) toast("Nothing to retell for this passage.", "err");
  }

  if (params.ref) retell(params.ref);
  return () => { if (unbind) unbind(); if (scene) scene.stop(); };
}

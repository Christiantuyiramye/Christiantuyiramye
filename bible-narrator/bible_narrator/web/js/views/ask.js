// Ask a question: answers grounded in the local library, with citations.
import { api } from "../api.js";
import { player } from "../player.js";
import { store } from "../store.js";
import { el, icon, segmented } from "../ui.js";

const thread = []; // kept while the app is open

export function renderAsk(root) {
  let detail = store.settings.answer_detail || "brief";
  const list = el("div", { class: "thread", "aria-live": "polite" });
  const box = el("textarea", { rows: "1", placeholder: "Ask about the Bible or your reference books…", "aria-label": "Your question" });
  const send = el("button", { class: "btn primary icon-only", "aria-label": "Ask", title: "Ask (Enter)" }, icon("upload"));
  root.append(el("div", { class: "ask-layout" },
    el("div", { class: "spread", style: { marginBottom: "16px" } },
      el("div", {}, el("div", { class: "eyebrow" }, "Ask a question"), el("h1", {}, "Answers from your library")),
      segmented([["brief", "Brief"], ["detailed", "More detail"]], detail, (v) => { detail = v; store.saveSettings({ answer_detail: v }); })),
    el("div", { class: "notice", style: { marginBottom: "18px" } }, icon("shield"),
      el("span", {}, "Answers come only from the Bibles and books in your library, with citations. If your library doesn't support an answer, you'll be told plainly. ",
        el("b", {}, "Scripture"), " and ", el("b", {}, "commentary/reference books"), " are always labeled separately.")),
    !store.modelReady() ? el("div", { class: "notice warn", style: { marginBottom: "18px" } }, icon("info"),
      el("span", {}, "No language model is installed, so you'll get matching passages instead of written answers. ",
        el("button", { class: "btn small", onclick: () => window.bnNavigate("settings", { section: "model" }) }, "Set up a model"))) : null,
    list,
    el("div", { class: "composer" }, el("div", { class: "box" }, box, send)),
  ));
  for (const t of thread) list.append(t.q, t.a);
  if (!thread.length) {
    list.append(el("div", { class: "row wrap small muted" }, "Examples:",
      ...["Who was Melchizedek?", "What happened at the Jordan when Jesus was baptized?", "What does Psalm 23 say about the shepherd?"].map((q) =>
        el("button", { class: "chip", onclick: () => { box.value = q; ask(); } }, q))));
  }
  box.addEventListener("input", () => { box.style.height = "auto"; box.style.height = `${box.scrollHeight}px`; });
  box.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } });
  send.onclick = () => ask();

  async function ask(question = box.value.trim(), level = detail) {
    if (!question) return;
    box.value = ""; box.style.height = "auto";
    if (list.querySelector(".row.wrap.small")) list.querySelector(".row.wrap.small").remove();
    const q = el("div", { class: "q-bubble" }, question);
    const a = el("div", { class: "card a-card" }, el("div", { class: "row muted" }, el("span", { class: "spinner" }),
      store.modelReady() ? "Searching your library and checking the answer…" : "Searching your library…"));
    thread.push({ q, a });
    list.append(q, a);
    a.scrollIntoView({ behavior: "smooth", block: "end" });
    try {
      const r = await api.post("/api/ask", { question, detail: level, source_id: store.translationId() });
      a.replaceChildren(...renderAnswer(r, (lvl) => ask(question, lvl)));
    } catch (e) {
      a.replaceChildren(el("div", { class: "notice err" }, icon("info"), e.message));
    }
  }
}

function renderAnswer(r, reask) {
  const parts = [];
  if (r.status === "not_found") {
    parts.push(el("div", { class: "notfound" }, r.answer));
  } else if (r.status === "no_model") {
    parts.push(el("div", { class: "eyebrow" }, "Search results — not an answer"));
  } else if (r.status === "error") {
    parts.push(el("div", { class: "notice err" }, icon("info"), (r.notes || [])[0] || "Something went wrong."));
  } else {
    const ans = el("div", { class: "answer" });
    r.segments.forEach((seg) => {
      ans.append(seg.text, " ");
      seg.cites.forEach((n) => ans.append(el("button", { class: "cite", title: "Show source", onclick: () => flash(n) }, String(n))));
      ans.append(" ");
    });
    const badge = r.status === "partial" ? el("span", { class: "badge" }, "Partial answer") :
      r.status === "disagree" ? el("span", { class: "badge" }, "Sources differ") : el("span", { class: "badge accent" }, "From your library");
    parts.push(el("div", { class: "row", style: { marginBottom: "10px" } }, badge, r.model ? el("span", { class: "small muted" }, `Checked against ${r.citations.length} source(s) · ${r.model}`) : null), ans);
  }
  for (const n of r.notes || []) if (r.status !== "error") parts.push(el("div", { class: "notice", style: { marginTop: "10px" } }, icon("info"), n));

  const sourcesList = r.citations.length ? r.citations : r.related;
  const sourcesWrap = el("div", { class: "sources" });
  const heading = r.citations.length ? "Sources" : (r.related || []).length ? (r.status === "no_model" ? "Passages matching your words" : "Closest passages searched (they don't answer the question)") : null;
  for (const s of sourcesList || []) {
    sourcesWrap.append(el("div", { class: `source ${s.is_scripture ? "scripture" : "ref"}`, dataset: { n: String(s.n) } },
      el("div", { class: "src-head" },
        el("b", {}, `[${s.n}]`),
        el("span", { class: s.is_scripture ? "chip scripture" : "chip reference" }, s.is_scripture ? "Scripture" : `${s.kind_label} · not Scripture`),
        el("b", {}, s.is_scripture ? `${s.label} (${s.abbreviation || s.title})` : s.title),
        !s.is_scripture && s.label ? el("span", { class: "small muted" }, s.label) : null,
        s.is_scripture ? el("button", { class: "btn small ghost", onclick: () => window.bnNavigate("read", { ref: s.label }) }, "Open") : null),
      el("div", { class: "src-text" }, s.text.length > 700 ? `${s.text.slice(0, 700)}…` : s.text),
      el("div", { class: "small muted", style: { marginTop: "6px" } }, `${s.title}${s.edition ? ` · ${s.edition}` : ""} · ${s.license || "license not specified"}`)));
  }
  if (heading) parts.push(el("h3", { style: { marginTop: "18px" } }, heading), sourcesWrap);
  if (r.removed && r.removed.length) {
    parts.push(el("details", { class: "removed", style: { marginTop: "10px" } },
      el("summary", {}, `Statements withheld by the accuracy checks (${r.removed.length})`),
      el("ul", {}, ...r.removed.map((x) => el("li", {}, `“${x.text}” — ${x.reason}`)))));
  }
  const actions = el("div", { class: "row wrap", style: { marginTop: "14px" } });
  if (r.segments && r.segments.length) {
    actions.append(el("button", { class: "btn small", onclick: () => player.load({
      id: `answer:${Date.now()}`, kind: "answer", title: r.question, subtitle: "Answer from your library",
      items: r.segments.map((s, i) => ({ key: `a${i}`, text: s.text, label: "Answer" })) }) }, icon("volume", 14), "Listen"));
    if (r.detail !== "detailed") actions.append(el("button", { class: "btn small", onclick: () => reask("detailed") }, "More detail"));
  }
  if (actions.childNodes.length) parts.push(actions);

  function flash(n) {
    const node = sourcesWrap.querySelector(`[data-n="${n}"]`);
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "center" });
    node.classList.remove("flash"); void node.offsetWidth; node.classList.add("flash");
  }
  return parts;
}

import { api } from "../api.js";
import { player } from "../player.js";
import { store } from "../store.js";
import { openSleepMode } from "../sleep.js";
import { el, icon, swatch } from "../ui.js";

export async function renderHome(root) {
  const go = (v, p) => window.bnNavigate(v, p);
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  root.append(
    el("div", { class: "hero" },
      el("div", {}, el("div", { class: "eyebrow" }, greet), el("h1", {}, "What would you like to do?"),
        el("p", {}, "Listen to Scripture, hear a short retelling of a passage, or ask a question answered from your own library — all offline.")),
      el("div", { class: "row wrap", style: { justifyContent: "flex-end" } },
        el("button", { class: "btn", onclick: () => go("read", { ref: store.settings.last_passage || "John 1" }) }, icon("book"), `Continue ${store.settings.last_passage || "John 1"}`),
        el("button", { class: "btn primary", onclick: () => openSleepMode() }, icon("moon"), "Sleep mode")),
    ),
    el("div", { class: "mode-cards" },
      modeCard("read", "book", "Read Scripture", "Verse by verse, a chapter, or Auto mode from beginning to end", () => go("read")),
      modeCard("retell", "film", "Retell a passage", "A short, faithful retelling with coloured story animation", () => go("story")),
      modeCard("ask", "chat", "Ask a question", "Answers grounded in your library, with citations", () => go("ask")),
    ),
  );

  const recCard = el("div", { class: "card" },
    el("div", { class: "spread" }, el("div", {}, el("div", { class: "eyebrow" }, "Suggested for you"), el("h2", {}, "What to read next")),
      el("span", { class: "chip", title: "Suggestions are computed on this computer from your local reading history." }, icon("shield", 14), "On-device")),
  );
  const list = el("div", { class: "rec-list", style: { marginTop: "14px" } }, el("div", { class: "empty" }, el("span", { class: "spinner" })));
  recCard.append(list);
  const side = el("div", { class: "grid" },
    el("div", { class: "card sleep-card" },
      el("div", { class: "eyebrow", style: { color: "#9a98b5" } }, "Sleep mode"),
      el("h3", { style: { margin: "6px 0" } }, "Drift off to a calm voice"),
      el("p", { class: "muted small" }, "Set a timer; the reading fades out gently and the screen dims."),
      el("button", { class: "btn accent", onclick: () => openSleepMode() }, icon("moon"), "Set sleep timer")),
    el("div", { class: "card flat" },
      el("div", { class: "eyebrow" }, "Your library"),
      el("p", { class: "small" }, `${store.status.library.scripture} Bible translation(s) · ${store.status.library.reference} reference book(s)`),
      el("button", { class: "btn small", onclick: () => go("library") }, "Manage library")),
  );
  root.append(el("div", { class: "home-grid" }, recCard, side));

  try {
    const r = await api.get("/api/recommendations");
    list.replaceChildren();
    if (r.basis === "disabled") {
      list.append(el("div", { class: "notice" }, icon("info"), "Reading history is off, so there are no personal suggestions. You can turn it on in Settings."));
    }
    for (const it of r.items) {
      list.append(el("button", { class: "rec", onclick: () => go("read", { ref: it.reference }) },
        el("div", { class: "swatch", style: { background: swatch(it.reference) } }),
        el("div", { class: "meta" }, el("b", {}, it.reference), el("span", {}, it.reason)),
        icon("chevronR")));
    }
    if (r.basis === "starter") list.append(el("p", { class: "muted small" }, "As you read and listen, suggestions adapt to what you spend time with."));
  } catch (e) {
    list.replaceChildren(el("div", { class: "notice err" }, e.message));
  }
  if (player.playlist) {
    root.prepend(el("div", { class: "notice", style: { marginBottom: "16px" } }, icon("volume"), `Now playing: ${player.playlist.title}`));
  }
}

function modeCard(cls, ic, title, text, onclick) {
  return el("button", { class: `mode-card ${cls}`, onclick },
    el("div", { class: "icon-badge" }, icon(ic, 22)),
    el("h3", {}, title), el("p", {}, text));
}

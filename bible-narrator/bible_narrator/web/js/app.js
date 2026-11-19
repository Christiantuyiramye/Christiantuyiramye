// App shell: routing, theme, status indicators, global passage/search box.
import { api } from "./api.js";
import { store } from "./store.js";
import { mountPlayerBar } from "./playerbar.js";
import { clear, el, hydrateIcons, icon, modal, toast } from "./ui.js";
import { renderHome } from "./views/home.js";
import { renderRead } from "./views/read.js";
import { renderStory } from "./views/story.js";
import { renderAsk } from "./views/ask.js";
import { renderLibrary } from "./views/library.js";
import { renderVoices } from "./views/voices.js";
import { renderSettings } from "./views/settings.js";
import { openOnboarding } from "./views/onboarding.js";

const VIEWS = { home: renderHome, read: renderRead, story: renderStory, ask: renderAsk, library: renderLibrary, voices: renderVoices, settings: renderSettings };
let currentView = null;
let cleanup = null;

export function navigate(view, params = {}) {
  if (!VIEWS[view]) view = "home";
  const main = document.getElementById("main");
  if (cleanup) { try { cleanup(); } catch { /* ignore */ } cleanup = null; }
  clear(main);
  currentView = view;
  document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  const container = el("div", { class: "view" });
  main.append(container);
  main.scrollTop = 0;
  Promise.resolve(VIEWS[view](container, params)).then((c) => { cleanup = typeof c === "function" ? c : null; })
    .catch((e) => { container.append(el("div", { class: "notice err" }, icon("info"), e.message || String(e))); });
}
window.bnNavigate = navigate;

function applyTheme() {
  const s = store.settings;
  document.documentElement.dataset.theme = s.theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.motion = s.reduce_motion ? "reduce" : "";
  document.documentElement.style.setProperty("--read-size", `${s.font_size || 20}px`);
  const t = document.getElementById("theme-toggle");
  t.replaceChildren(icon(s.theme === "dark" ? "sun" : "moon"));
}

function renderStatus(st) {
  const set = (id, cls, text, title) => {
    const b = document.getElementById(id);
    b.querySelector(".led").className = `led ${cls}`;
    b.querySelector("span:last-child").textContent = text;
    b.title = title;
  };
  const llm = st.llm;
  const model = {
    ready: ["ok", `AI: ${llm.model}`, "Language model loaded and running on this computer."],
    idle: ["ok", `AI: ${llm.model}`, "Language model selected (loads on first use)."],
    loading: ["busy", "AI: loading…", "Loading the language model into memory."],
    error: ["err", "AI: error", llm.error || "The language model could not be loaded."],
    not_configured: ["warn", "AI: not installed", "No language model yet. Reading and narration work; Retell and Ask need a model."],
  }[llm.state] || ["warn", "AI", ""];
  set("pill-model", ...model);
  const k = st.tts.kokoro;
  if (k.installed) set("pill-voice", "ok", `Voices: ${st.tts.voice_count}`, `${k.voices} natural Kokoro voices + basic voices installed.`);
  else set("pill-voice", "warn", "Voices: basic", "Only the basic (robotic) voices are installed. Download natural voices in Voices.");
  if (st.network.downloading) set("pill-offline", "busy", "Downloading", "A model download you started is using the internet.");
  else set("pill-offline", "ok", "Offline · private", st.network.statement + " No accounts, analytics or telemetry.");
}

async function boot() {
  hydrateIcons();
  try {
    await Promise.all([store.refreshStatus(), store.refreshVoices(), store.refreshSources()]);
  } catch (e) {
    document.getElementById("main").append(el("div", { class: "view" }, el("div", { class: "notice err" }, icon("info"), e.message)));
    return;
  }
  applyTheme();
  renderStatus(store.status);
  mountPlayerBar(document.getElementById("player"));
  store.on("settings", applyTheme);
  store.on("status", renderStatus);
  setInterval(() => store.refreshStatus().catch(() => {}), 4000);

  document.getElementById("nav").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-view]");
    if (b) navigate(b.dataset.view);
  });
  document.getElementById("theme-toggle").onclick = () => store.saveSettings({ theme: store.settings.theme === "dark" ? "light" : "dark" });
  document.getElementById("pill-model").onclick = () => navigate("settings", { section: "model" });
  document.getElementById("pill-voice").onclick = () => navigate("voices");
  document.getElementById("pill-offline").onclick = showPrivacy;
  document.getElementById("global-search").addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = document.getElementById("global-search-input").value.trim();
    if (!q) return;
    const res = await api.get(`/api/search?${api.qs({ q })}`).catch((err) => { toast(err.message, "err"); return null; });
    if (!res) return;
    if (res.reference_match) navigate("read", { ref: q });
    else navigate("library", { search: q, results: res });
  });

  navigate("home");
  if (!store.settings.onboarding_complete) openOnboarding();
}

function showPrivacy() {
  modal(el("div", { class: "stack" },
    el("div", { class: "eyebrow" }, "Privacy"),
    el("h2", {}, "Everything stays on this computer"),
    el("ul", { class: "stack" },
      el("li", {}, "Reading, narration, search, retelling and answers run locally. Your questions and documents are never sent anywhere."),
      el("li", {}, "No accounts, analytics, telemetry or remote AI services."),
      el("li", {}, "The only internet use is a download you start yourself (a language model or natural voices). You can also copy those files in by hand."),
      el("li", {}, "Reading history (for suggestions) is stored only in your local library and can be switched off or cleared in Settings."),
    ),
    el("p", { class: "muted small" }, `Data folder: ${store.status.app.data_dir}`),
  ));
}

boot();

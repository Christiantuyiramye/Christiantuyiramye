// Settings: appearance, playback, sleep, language model, privacy, about.
import { api, nativePick } from "../api.js";
import { player } from "../player.js";
import { store } from "../store.js";
import { el, fmtBytes, icon, segmented, toast, toggle } from "../ui.js";

function setting(label, sub, control) {
  return el("div", { class: "setting" }, el("div", { class: "label" }, el("b", {}, label), sub ? el("span", {}, sub) : null), control);
}

export async function modelSection(onChange) {
  const wrap = el("div");
  let timer = null;
  async function draw() {
    const cat = await api.get("/api/models/catalog");
    const llm = cat.llm;
    const stateText = {
      ready: `Loaded: ${llm.model}`, idle: `Selected: ${llm.model} (loads on first use)`, loading: `Loading ${llm.model}…`,
      error: `Error: ${llm.error}`, not_configured: "No model installed",
    }[llm.state] || llm.state;
    const path = el("input", { class: "input", placeholder: "Path to a .gguf model file", style: { flex: 1 } });
    const usePath = async (p) => {
      try { await api.post("/api/models/use", { path: p }); toast("Model selected. It loads in the background."); await store.refreshStatus(); draw(); onChange && onChange(); }
      catch (e) { toast(e.message, "err"); }
    };
    const choose = el("button", { class: "btn" }, icon("folder", 16), "Choose file…");
    choose.onclick = async () => {
      const p = await nativePick("gguf");
      if (p === undefined) { path.focus(); toast("Type or paste the path to the .gguf file, then press Use file."); return; }
      if (p) usePath(p);
    };
    const rows = cat.catalog.filter((c) => c.type === "llm").map((c) => {
      const job = c.job;
      const btn = c.installed
        ? el("button", { class: "btn small", onclick: () => usePath(c.path) }, llm.path === c.path ? "In use" : "Use")
        : job && job.state === "running"
          ? el("div", { class: "small muted" }, `${fmtBytes(job.done_bytes)} / ~${fmtBytes(job.total_bytes)}`)
          : el("button", { class: "btn small primary", onclick: async () => { try { await api.post("/api/downloads", { id: c.id }); poll(); draw(); } catch (e) { toast(e.message, "err"); } } }, icon("download", 14), `Download ${fmtBytes(c.size_mb * 1e6)}`);
      return el("div", { class: "model-row" },
        el("div", { class: "grow" }, el("b", {}, c.title), el("div", { class: "small muted" }, c.description),
          el("div", { class: "small muted" }, `License: ${c.license} · ${c.origin}`)), btn);
    });
    const jobs = (await api.get("/api/downloads")).jobs.filter((j) => j.state === "error");
    wrap.replaceChildren(
      el("div", { class: "row" }, el("span", { class: `led ${llm.state === "ready" || llm.state === "idle" ? "ok" : llm.state === "loading" ? "busy" : llm.state === "error" ? "err" : "warn"}`, style: { width: "10px", height: "10px", borderRadius: "50%", display: "inline-block" } }), el("b", {}, stateText)),
      el("p", { class: "small muted" }, "The model runs on this computer with llama.cpp. It only writes from passages retrieved from your library, and every sentence is checked against them. Reading and narration work without a model; Retell and Ask need one."),
      ...jobs.map((j) => el("div", { class: "notice err" }, icon("info"), `${j.title}: ${j.error}`)),
      el("h3", { style: { marginTop: "12px" } }, "Download an open-weight model"),
      el("p", { class: "small muted" }, "Downloads happen only when you click. Files are saved to: " + cat.models_dir),
      ...rows,
      el("h3", { style: { marginTop: "16px" } }, "Or use a GGUF file you already have"),
      el("div", { class: "row wrap" }, choose),
      el("div", { class: "row", style: { marginTop: "8px" } }, path, el("button", { class: "btn small", onclick: () => path.value.trim() && usePath(path.value.trim()) }, "Use file")),
      cat.local_models.length ? el("div", { class: "small muted", style: { marginTop: "8px" } }, "Found in your models folder: ",
        ...cat.local_models.map((m) => el("button", { class: "chip", onclick: () => usePath(m) }, m.split(/[\\/]/).pop()))) : null,
      el("details", { style: { marginTop: "14px" } }, el("summary", { style: { cursor: "pointer" } }, "Advanced: use a model server on this computer (Ollama, LM Studio)"),
        localServer()),
    );
  }
  function localServer() {
    const s = store.settings;
    const url = el("input", { class: "input", value: s.local_server_url });
    const model = el("input", { class: "input", value: s.local_server_model, placeholder: "model name (optional)" });
    const save = el("button", { class: "btn small" }, "Use local server");
    save.onclick = async () => {
      try { await store.saveSettings({ llm_backend: "local_server", local_server_url: url.value.trim(), local_server_model: model.value.trim() }); toast("Using the local model server."); draw(); }
      catch (e) { toast(e.message, "err"); }
    };
    return el("div", { class: "stack", style: { marginTop: "10px" } },
      el("p", { class: "small muted" }, "Only addresses on this computer (localhost / 127.0.0.1) are accepted, so your text never leaves the machine."),
      el("label", { class: "field" }, el("span", {}, "OpenAI-compatible URL"), url), el("label", { class: "field" }, el("span", {}, "Model"), model), save);
  }
  function poll() {
    clearInterval(timer);
    timer = setInterval(async () => {
      const { jobs } = await api.get("/api/downloads");
      if (!jobs.some((j) => j.state === "running")) { clearInterval(timer); await store.refreshStatus(); }
      draw();
    }, 1500);
  }
  await draw();
  return wrap;
}

export async function renderSettings(root, params = {}) {
  const s = store.settings;
  const save = (v) => store.saveSettings(v).catch((e) => toast(e.message, "err"));
  const font = el("input", { type: "range", min: "15", max: "30", step: "1", value: String(s.font_size), "aria-label": "Reading text size" });
  font.oninput = () => document.documentElement.style.setProperty("--read-size", `${font.value}px`);
  font.onchange = () => save({ font_size: Number(font.value) });
  const sleepSel = el("select", { class: "input", style: { width: "auto" } }, ...[15, 30, 45, 60, 90].map((m) => el("option", { value: m }, `${m} minutes`)));
  sleepSel.value = String(s.sleep_minutes);
  sleepSel.onchange = () => save({ sleep_minutes: Number(sleepSel.value) });
  const fadeSel = el("select", { class: "input", style: { width: "auto" } }, ...[15, 30, 60, 120].map((m) => el("option", { value: m }, `${m} s`)));
  fadeSel.value = String(s.sleep_fade_seconds);
  fadeSel.onchange = () => save({ sleep_fade_seconds: Number(fadeSel.value) });

  const appearance = el("div", { class: "card" }, el("h2", {}, "Appearance"),
    setting("Theme", "Light or black mode", segmented([["light", "Light"], ["dark", "Black"]], s.theme === "dark" ? "dark" : "light", (v) => save({ theme: v }))),
    setting("Reading text size", "Size of Scripture text", font),
    setting("Coloured story animation", "Animated scenes while narrating in Retell", toggle(s.story_visuals, (v) => save({ story_visuals: v }))),
    setting("Reduce motion", "Keep scenes and transitions still", toggle(s.reduce_motion, (v) => save({ reduce_motion: v }))));
  const playback = el("div", { class: "card" }, el("h2", {}, "Reading & playback"),
    setting("Announce the passage", "Say “John, chapter 3” before reading", toggle(s.announce_passage, (v) => save({ announce_passage: v }))),
    setting("Auto mode", "Keep reading into the next chapter, through to Revelation", toggle(s.auto_continue, (v) => save({ auto_continue: v }))),
    setting("Follow along", "Scroll to the verse being read", toggle(s.auto_scroll, (v) => save({ auto_scroll: v }))),
    setting("Default voice", store.voiceLabel(s.default_voice), el("button", { class: "btn small", onclick: () => window.bnNavigate("voices") }, "Change")),
    setting("Speed and volume", `${s.playback_rate}× · ${Math.round(s.volume * 100)}% (also in the player)`, el("span")),
    setting("Sleep timer default", "Used by Sleep mode", sleepSel),
    setting("Sleep fade-out", "How long the voice fades at the end", fadeSel));
  const modelCard = el("div", { class: "card", id: "model" }, el("h2", {}, "Language model (AI)"), await modelSection());
  const privacy = el("div", { class: "card" }, el("h2", {}, "Privacy"),
    el("div", { class: "notice", style: { margin: "8px 0" } }, icon("shield"), "No accounts, analytics, telemetry or cloud AI. Everything runs on this computer."),
    setting("Reading history", "Used only on this computer to suggest what to read next", toggle(s.history_enabled, (v) => save({ history_enabled: v }))),
    setting("Clear reading history", "", el("button", { class: "btn small", onclick: async () => { await api.del("/api/history"); toast("Reading history cleared."); } }, "Clear")),
    setting("Clear audio cache", "Synthesized speech is cached to replay instantly", el("button", { class: "btn small", onclick: async () => { const r = await api.del("/api/audio-cache"); player.clips.clear(); toast(`Removed ${r.removed} cached clips.`); } }, "Clear")),
    setting("Data folder", store.status.app.data_dir, el("span")),
    setting("Show welcome guide again", "", el("button", { class: "btn small", onclick: async () => { const m = await import("./onboarding.js"); m.openOnboarding(); } }, "Open")));
  const about = el("div", { class: "card" }, el("h2", {}, "About & licenses"),
    el("p", { class: "small" }, `Bible Narrator ${store.status.app.version} — open source (MIT).`),
    el("ul", { class: "small muted stack" },
      el("li", {}, "Bundled texts: Berean Standard Bible (CC0), King James Version (public domain; Crown patent in the UK), American Standard Version (public domain), Easton's Bible Dictionary (1897, public domain; digital edition CC BY-SA 4.0 by Theographic)."),
      el("li", {}, "Natural voices: Kokoro-82M (Apache-2.0). Basic voices and phonemizer: eSpeak NG (GPL-3.0)."),
      el("li", {}, "Language models you add keep their own licenses (shown before download)."),
      el("li", {}, "Fonts: Outfit and Literata (SIL Open Font License 1.1).")));
  root.append(el("div", {}, el("div", { class: "eyebrow" }, "Settings"), el("h1", { style: { marginBottom: "16px" } }, "Preferences")),
    el("div", { class: "settings-grid" }, el("div", { class: "grid" }, appearance, playback, privacy), el("div", { class: "grid", style: { alignContent: "start" } }, modelCard, about)));
  if (params.section === "model") modelCard.scrollIntoView({ behavior: "smooth" });
}

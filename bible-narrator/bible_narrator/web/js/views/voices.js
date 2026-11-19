// Voices: preview every installed voice, choose the default, install natural voices.
import { api, nativePick } from "../api.js";
import { player } from "../player.js";
import { store } from "../store.js";
import { el, fmtBytes, icon, segmented, swatch, toast } from "../ui.js";

const SAMPLE = "The Lord is my shepherd; I shall not want. He makes me lie down in green pastures.";
const previewAudio = new Audio();

export async function previewVoice(id, btn) {
  try {
    if (btn) btn.replaceChildren(el("span", { class: "spinner" }));
    const res = await api.raw("POST", "/api/tts", { voice: id, text: SAMPLE });
    previewAudio.src = URL.createObjectURL(await res.blob());
    previewAudio.volume = player.volume;
    await previewAudio.play();
  } catch (e) { toast(e.message, "err"); }
  finally { if (btn) btn.replaceChildren(icon("play", 16)); }
}

export async function kokoroCard(onChange) {
  const cat = await api.get("/api/models/catalog");
  const item = cat.catalog.find((c) => c.type === "voices");
  const st = store.status.tts.kokoro;
  const card = el("div", { class: "card" });
  const draw = (job) => {
    card.replaceChildren(
      el("div", { class: "spread" },
        el("div", {}, el("div", { class: "eyebrow" }, "Natural voices"), el("h2", {}, "Kokoro-82M")),
        st.installed ? el("span", { class: "badge accent" }, `Installed · ${st.voices} voices`) : el("span", { class: "badge" }, "Download needed")),
      el("p", { class: "muted" }, item.description),
      el("div", { class: "small muted" }, `License: ${item.license} · Size: about ${item.size_mb} MB · From ${item.origin}`),
    );
    if (st.installed) {
      card.append(el("div", { class: "small muted", style: { marginTop: "8px" } }, `Folder: ${st.folder}`));
    } else {
      const progress = el("div", { class: "progress", style: { margin: "12px 0" } }, el("div"));
      const dl = el("button", { class: "btn primary" }, icon("download", 16), `Download (${item.size_mb} MB)`);
      dl.onclick = async () => { try { draw(await api.post("/api/downloads", { id: item.id })); poll(); } catch (e) { toast(e.message, "err"); } };
      const folderInput = el("input", { class: "input", placeholder: "Folder with model .onnx and voice .bin files", style: { flex: 1 } });
      const useFolder = async (path) => {
        try {
          await api.post("/api/voices/kokoro-folder", { path }); toast("Natural voices installed.");
          await store.refreshStatus(); await store.refreshVoices(); store.emit("settings", store.settings); onChange && onChange();
        }
        catch (e) { toast(e.message, "err"); }
      };
      const pick = el("button", { class: "btn" }, icon("folder", 16), "Choose folder…");
      pick.onclick = async () => {
        const p = await nativePick("folder");
        if (p === undefined) { folderInput.focus(); toast("Type or paste the folder path, then press Use folder."); return; }
        if (p) useFolder(p);
      };
      card.append(...[
        el("div", { class: "notice warn", style: { marginTop: "12px" } }, icon("info"),
          "Natural voices need a one-time download. This is the only time the app uses the internet, and only when you click Download. Until then, the basic voices below work offline."),
        job && job.state === "running" ? el("div", {}, progress, el("div", { class: "small muted" }, `Downloading ${job.file}… ${fmtBytes(job.done_bytes)} of ~${fmtBytes(job.total_bytes)}`),
          el("button", { class: "btn small", onclick: () => api.post(`/api/downloads/${job.id}/cancel`) }, "Cancel")) : null,
        job && job.state === "error" ? el("div", { class: "notice err", style: { marginTop: "10px" } }, icon("info"), job.error) : null,
        el("div", { class: "row wrap", style: { marginTop: "12px" } }, dl, pick),
        el("div", { class: "row", style: { marginTop: "10px" } }, folderInput, el("button", { class: "btn small", onclick: () => folderInput.value.trim() && useFolder(folderInput.value.trim()) }, "Use folder")),
        el("p", { class: "small muted" }, item.manual),
      ].filter(Boolean));
      if (job && job.state === "running") progress.firstChild.style.width = `${Math.min(100, (100 * job.done_bytes) / job.total_bytes)}%`;
    }
  };
  let timer = null;
  const poll = () => {
    clearInterval(timer);
    timer = setInterval(async () => {
      const { jobs } = await api.get("/api/downloads");
      const job = jobs.filter((j) => j.item_id === item.id).pop();
      if (!job) return;
      if (job.state !== "running") {
        clearInterval(timer);
        await store.refreshStatus(); await store.refreshVoices();
        if (job.state === "done") { toast("Natural voices installed."); onChange && onChange(); return; }
      }
      draw(job);
    }, 1000);
  };
  draw(item.job);
  if (item.job) poll();
  return card;
}

export async function renderVoices(root) {
  let filter = "all";
  const grid = el("div", { class: "voice-grid" });
  root.append(
    el("div", {}, el("div", { class: "eyebrow" }, "Voices"), el("h1", {}, "Choose a narrator")),
    el("p", { class: "muted" }, "Preview any voice, then make it your default. You can also switch voices from the player at any time."),
  );
  const kc = await kokoroCard(() => window.bnNavigate("voices"));
  root.append(kc,
    el("div", { class: "spread", style: { margin: "22px 0 4px" } }, el("h2", {}, `Installed voices (${store.voices.length})`),
      segmented([["all", "All"], ["kokoro", "Natural"], ["espeak", "Basic"], ["female", "Female"], ["male", "Male"]], filter, (v) => { filter = v; draw(); })),
    grid,
    el("p", { class: "small muted", style: { marginTop: "16px" } },
      "Natural voices: Kokoro-82M, Apache-2.0. Basic voices: eSpeak NG, GPL-3.0 (bundled). Every voice listed here produces genuinely different audio; none are placeholders."));

  function draw() {
    grid.replaceChildren();
    const def = store.settings.default_voice;
    const vs = store.voices.filter((v) => filter === "all" || v.engine === filter || v.gender === filter);
    for (const v of vs) {
      const playB = el("button", { class: "btn icon-only", "aria-label": `Preview ${v.label}`, title: "Preview" }, icon("play", 16));
      playB.onclick = () => previewVoice(v.id, playB);
      const isDef = v.id === def;
      const setB = el("button", { class: `check-circle ${isDef ? "on" : ""}`, title: isDef ? "Default voice" : "Make default", "aria-label": isDef ? "Default voice" : `Make ${v.label} the default voice`, style: { cursor: "pointer" } }, isDef ? icon("check", 14) : "");
      setB.onclick = async () => { await store.saveSettings({ default_voice: v.id }); player.setVoice(v.id); toast(`${v.label} is now your default voice.`); draw(); };
      grid.append(el("div", { class: `voice ${isDef ? "default" : ""}` },
        el("div", { class: "avatar", style: { background: swatch(v.id) } }, v.label.replace("Basic · ", "").slice(0, 1)),
        el("div", { class: "info" }, el("b", {}, v.label), el("span", {}, `${v.accent} · ${v.gender} · ${v.quality}`)),
        playB, setB));
    }
  }
  draw();
}

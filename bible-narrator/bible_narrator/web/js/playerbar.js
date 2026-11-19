// Persistent bottom player: play/pause, verse navigation, seek, speed, volume,
// voice, sleep timer and story view.
import { player } from "./player.js";
import { store } from "./store.js";
import { openTheater } from "./story.js";
import { openSleepMode } from "./sleep.js";
import { el, fmtTime, icon, swatch } from "./ui.js";

export function mountPlayerBar(root) {
  const art = el("div", { class: "art", title: "Open story view", role: "button", tabindex: "0" });
  const title = el("b", {}, "Nothing playing");
  const sub = el("span", {}, "Pick a passage to listen");
  const playBtn = el("button", { class: "play-btn", "aria-label": "Play", title: "Play / pause (Space)" }, icon("play", 20));
  const prevBtn = el("button", { class: "btn ghost icon-only", "aria-label": "Previous verse", title: "Previous verse (←)" }, icon("prev"));
  const nextBtn = el("button", { class: "btn ghost icon-only", "aria-label": "Next verse", title: "Next verse (→)" }, icon("next"));
  const seek = el("input", { type: "range", min: "0", max: "100", step: "0.1", value: "0", "aria-label": "Seek" });
  const tCur = el("span", {}, "0:00");
  const tTot = el("span", {}, "0:00");
  const rate = el("select", { "aria-label": "Playback speed", title: "Playback speed" },
    ...[0.75, 0.85, 1, 1.1, 1.25, 1.5, 1.75, 2].map((r) => el("option", { value: r }, `${r}×`)));
  const vol = el("input", { type: "range", class: "vol", min: "0", max: "1", step: "0.05", "aria-label": "Volume", title: "Volume" });
  const voice = el("select", { "aria-label": "Voice", title: "Voice" });
  const sleepBtn = el("button", { class: "btn ghost icon-only", title: "Sleep timer & sleep mode", "aria-label": "Sleep timer" }, icon("bed"));
  const storyBtn = el("button", { class: "btn ghost icon-only", title: "Story view (animated)", "aria-label": "Story view" }, icon("expand"));
  const buffering = el("span", { class: "spinner hidden", "aria-label": "Loading audio" });

  root.append(
    el("div", { class: "now" }, art, el("div", { class: "meta" }, title, sub), buffering),
    el("div", { class: "controls" }, prevBtn, playBtn, nextBtn),
    el("div", { class: "seek" }, tCur, seek, tTot),
    el("div", { class: "extras" }, icon("volume", 16), vol, rate, voice, sleepBtn, storyBtn),
  );

  playBtn.onclick = () => player.toggle();
  prevBtn.onclick = () => player.prev();
  nextBtn.onclick = () => player.next();
  art.onclick = storyBtn.onclick = () => openTheater();
  art.onkeydown = (e) => { if (e.key === "Enter") openTheater(); };
  sleepBtn.onclick = () => openSleepMode();
  let seeking = false;
  seek.addEventListener("input", () => { seeking = true; tCur.textContent = fmtTime(Number(seek.value)); });
  seek.addEventListener("change", () => { seeking = false; player.seekTo(Number(seek.value)); });
  rate.onchange = () => { player.setRate(rate.value); store.saveSettings({ playback_rate: Number(rate.value) }); };
  vol.oninput = () => player.setVolume(vol.value);
  vol.onchange = () => store.saveSettings({ volume: Number(vol.value) });
  voice.onchange = () => { player.setVoice(voice.value); store.saveSettings({ default_voice: voice.value }); };

  function fillVoices() {
    voice.replaceChildren();
    const groups = { kokoro: "Natural voices (Kokoro)", espeak: "Basic voices (eSpeak NG)" };
    for (const [eng, label] of Object.entries(groups)) {
      const vs = store.voices.filter((v) => v.engine === eng);
      if (!vs.length) continue;
      const og = el("optgroup", { label });
      vs.forEach((v) => og.append(el("option", { value: v.id }, `${v.label} — ${v.accent.replace(" English", "")} ${v.gender}`)));
      voice.append(og);
    }
    voice.value = player.voice || store.settings.default_voice;
  }

  store.on("voices", fillVoices);
  store.on("settings", (s) => { if (s.default_voice && s.default_voice !== player.voice) { player.setVoice(s.default_voice); voice.value = s.default_voice; } });
  store.on("player:voice", (id) => { voice.value = id; });
  store.on("player:load", (pl) => {
    root.classList.remove("idle");
    title.textContent = pl.title;
    sub.textContent = pl.subtitle;
    art.style.background = swatch(pl.title);
  });
  store.on("player:item", ({ item, playlist }) => {
    if (!item) return;
    sub.textContent = item.intro ? playlist.subtitle : `${item.label} · ${playlist.subtitle}`;
  });
  store.on("player:state", ({ playing }) => {
    playBtn.replaceChildren(icon(playing ? "pause" : "play", 20));
    playBtn.setAttribute("aria-label", playing ? "Pause" : "Play");
  });
  store.on("player:buffering", (b) => buffering.classList.toggle("hidden", !b));
  store.on("player:progress", ({ time, total }) => {
    seek.max = String(Math.max(1, total));
    if (!seeking) { seek.value = String(time); tCur.textContent = fmtTime(time); }
    tTot.textContent = fmtTime(total);
  });
  store.on("sleep:changed", (s) => sleepBtn.classList.toggle("sleep-active", !!s));
  store.on("sleep:tick", ({ remaining }) => { sleepBtn.title = `Sleep timer: ${fmtTime(remaining)} left`; });

  const s = store.settings;
  rate.value = String(s.playback_rate || 1);
  if (!rate.value) rate.value = "1";
  vol.value = String(s.volume ?? 0.9);
  player.configure({ rate: s.playback_rate || 1, volume: s.volume ?? 0.9, voice: s.default_voice });
  fillVoices();

  document.addEventListener("keydown", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    if (["input", "textarea", "select"].includes(tag) || e.target.isContentEditable || document.querySelector(".overlay, .theater")) return;
    if (e.key === " ") { e.preventDefault(); player.toggle(); }
    else if (e.key === "ArrowRight" && !e.shiftKey) player.next();
    else if (e.key === "ArrowLeft" && !e.shiftKey) player.prev();
    else if (e.key === "ArrowRight" && e.shiftKey) player.seekTo(player.globalTime() + 10);
    else if (e.key === "ArrowLeft" && e.shiftKey) player.seekTo(player.globalTime() - 10);
  });
}

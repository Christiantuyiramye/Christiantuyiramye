// Coloured animated "story scenes" drawn on a canvas, synced to narration, and
// exportable as a short video. The visuals are abstract (sky, land, water, light,
// particles). Each motif is chosen only from words that actually appear in the
// text being read, and nothing depicts people or invents scenes.
import { api } from "./api.js";
import { player } from "./player.js";
import { store } from "./store.js";
import { el, icon, toast } from "./ui.js";

const MOTIFS = [
  { name: "sea", words: ["sea", "seas", "water", "waters", "river", "rivers", "jordan", "flood", "waves", "wave", "deep", "rain", "lake", "fish", "boat", "ship", "nets", "net", "well", "springs"],
    sky: ["#06305c", "#1f8fcf", "#8fe3f5"], land: "waves", landColors: ["#0a4a7a", "#1677b5", "#33b1e3"], particles: "bubbles" },
  { name: "fire", words: ["fire", "flame", "flames", "burnt", "burning", "burned", "altar", "lamp", "lamps", "torch", "smoke", "furnace", "coals"],
    sky: ["#2a0612", "#a3242c", "#ffa23e"], land: "hills", landColors: ["#1a0509", "#3b0c14", "#5e1a1a"], particles: "embers" },
  { name: "night", words: ["night", "darkness", "dark", "evening", "stars", "star", "moon", "sleep", "slept", "dream", "dreamed", "midnight"],
    sky: ["#04061c", "#1b1f5c", "#4b3c8f"], land: "hills", landColors: ["#05061a", "#0d1033", "#1a1a4d"], particles: "stars", moon: true },
  { name: "light", words: ["light", "sun", "morning", "dawn", "glory", "shine", "shone", "shining", "bright", "brightness", "heavens", "heaven", "radiant"],
    sky: ["#ff8a3d", "#ffc65c", "#fff1b8"], land: "hills", landColors: ["#c8642a", "#e08a3c", "#f2b45a"], particles: "motes", sun: true },
  { name: "garden", words: ["garden", "tree", "trees", "vine", "vineyard", "fig", "olive", "field", "fields", "seed", "seeds", "grass", "harvest", "fruit", "plants", "flowers", "lilies", "branches", "leaves", "wheat", "sheep", "flock", "shepherd"],
    sky: ["#3aa676", "#9be1a8", "#effac7"], land: "hills", landColors: ["#1f6b45", "#2f8f57", "#5cb85c"], particles: "leaves" },
  { name: "mountain", words: ["mountain", "mountains", "mount", "hill", "hills", "rock", "rocks", "stone", "stones", "sinai", "zion", "moriah", "horeb", "cave", "carmel"],
    sky: ["#3c2a7d", "#a35ac9", "#ffb38a"], land: "mountains", landColors: ["#2a1f55", "#4a3384", "#7a52a8"], particles: "dust" },
  { name: "desert", words: ["wilderness", "desert", "sand", "dust", "camels", "camel", "tent", "tents", "journey", "egypt", "drought"],
    sky: ["#e2683c", "#f7a65a", "#ffe2a8"], land: "dunes", landColors: ["#b8642f", "#d98b45", "#f0b468"], particles: "dust" },
  { name: "wind", words: ["wind", "winds", "spirit", "breath", "storm", "cloud", "clouds", "whirlwind", "sky", "air", "thunder", "lightning", "tempest"],
    sky: ["#25425f", "#5b86ad", "#cfe3f2"], land: "hills", landColors: ["#1b2f45", "#2c4a68", "#47698c"], particles: "swirls" },
  { name: "city", words: ["city", "cities", "jerusalem", "temple", "house", "gate", "gates", "walls", "wall", "palace", "throne", "tower", "babylon", "nineveh"],
    sky: ["#5b2a86", "#c0508a", "#f7b267"], land: "city", landColors: ["#2a1240", "#3d1a5c", "#56287a"], particles: "motes" },
  { name: "feast", words: ["bread", "wine", "feast", "supper", "meal", "loaves", "eat", "ate", "cup", "table", "banquet", "wedding"],
    sky: ["#7a1d2c", "#d0533e", "#f8c471"], land: "hills", landColors: ["#4d1420", "#6e1f2a", "#923232"], particles: "motes" },
];
const DEFAULT = { name: "default", sky: ["#1d2b64", "#7a4fa3", "#f8cdda"], land: "hills", landColors: ["#1b1f4a", "#2f2f6e", "#53407f"], particles: "motes" };

export function motifsFor(text) {
  const words = (text || "").toLowerCase().match(/[a-z]+/g) || [];
  const counts = new Map();
  for (const m of MOTIFS) {
    let n = 0;
    for (const w of words) if (m.words.includes(w)) n++;
    if (n) counts.set(m, n);
  }
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([m]) => m);
  const matched = sorted.length ? sorted[0].words.filter((w) => words.includes(w)).slice(0, 3) : [];
  return { primary: sorted[0] || null, secondary: sorted[1] || null, matched };
}

const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
const rgb = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

export class StoryScene {
  constructor(canvas, { width = 1280, height = 720 } = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    canvas.width = width; canvas.height = height;
    this.w = width; this.h = height;
    this.motif = DEFAULT;
    this.prevMotif = DEFAULT;
    this.blend = 1;
    this.secondary = null;
    this.text = "";
    this.label = "";
    this.kindLabel = "";
    this.title = "";
    this.progress = 0;
    this.particles = [];
    this.t0 = performance.now();
    this.running = false;
    this.reduceMotion = false;
    this._seedParticles();
  }

  setSegment({ text, label, kindLabel, title, motifText }) {
    const m = motifsFor(motifText || text);
    const next = m.primary || this.motif || DEFAULT;
    if (next !== this.motif) {
      this.prevMotif = this.motif;
      this.motif = next;
      this.blend = 0;
      this._seedParticles();
    }
    this.secondary = m.secondary;
    this.matched = m.matched;
    this.text = text || "";
    this.label = label || "";
    this.kindLabel = kindLabel || "";
    if (title !== undefined) this.title = title;
    this.progress = 0;
    if (!this.running) this.draw(performance.now());
  }

  setProgress(p) { this.progress = Math.max(0, Math.min(1, p)); }

  start() {
    if (this.running) return;
    this.running = true;
    const loop = (now) => { if (!this.running) return; this.draw(now); this.raf = requestAnimationFrame(loop); };
    this.raf = requestAnimationFrame(loop);
  }
  stop() { this.running = false; cancelAnimationFrame(this.raf); }

  _seedParticles() {
    const kind = (this.motif || DEFAULT).particles;
    const n = { stars: 140, bubbles: 40, embers: 70, leaves: 28, dust: 60, swirls: 14, motes: 50 }[kind] || 40;
    this.particles = Array.from({ length: n }, () => ({
      x: Math.random() * this.w, y: Math.random() * this.h, r: Math.random(), s: 0.3 + Math.random(), p: Math.random() * Math.PI * 2,
    }));
  }

  draw(now) {
    const ctx = this.ctx, w = this.w, h = this.h;
    const t = this.reduceMotion ? 0 : (now - this.t0) / 1000;
    this.blend = Math.min(1, this.blend + 0.02);
    const sky = [0, 1, 2].map((i) => mix(hex(this.prevMotif.sky[i]), hex(this.motif.sky[i]), this.blend));
    const land = [0, 1, 2].map((i) => mix(hex(this.prevMotif.landColors[i]), hex(this.motif.landColors[i]), this.blend));

    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, rgb(sky[0])); g.addColorStop(0.55, rgb(sky[1])); g.addColorStop(1, rgb(sky[2]));
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);

    // Soft glow (sun or moon) only for light/night motifs
    if (this.motif.sun || this.motif.moon) {
      const cx = w * 0.72, cy = h * 0.3 + Math.sin(t * 0.2) * 6;
      const glow = ctx.createRadialGradient(cx, cy, 10, cx, cy, 260);
      glow.addColorStop(0, this.motif.sun ? "rgba(255,248,214,0.95)" : "rgba(235,235,255,0.9)");
      glow.addColorStop(0.25, this.motif.sun ? "rgba(255,214,120,0.45)" : "rgba(170,170,230,0.25)");
      glow.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = glow; ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = this.motif.sun ? "#fff6d5" : "#e9e7ff";
      ctx.beginPath(); ctx.arc(cx, cy, this.motif.sun ? 56 : 40, 0, Math.PI * 2); ctx.fill();
      if (this.motif.moon) { ctx.fillStyle = rgb(sky[0]); ctx.beginPath(); ctx.arc(cx + 16, cy - 10, 38, 0, Math.PI * 2); ctx.fill(); }
    }
    this._particles(t, "back");
    this._land(t, land);
    this._particles(t, "front");

    // Vignette + caption panel
    const v = ctx.createRadialGradient(w / 2, h / 2, h * 0.3, w / 2, h / 2, h * 0.95);
    v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,0.45)");
    ctx.fillStyle = v; ctx.fillRect(0, 0, w, h);
    this._caption();
  }

  _land(t, colors) {
    const ctx = this.ctx, w = this.w, h = this.h;
    const kind = this.motif.land;
    for (let layer = 0; layer < 3; layer++) {
      ctx.fillStyle = rgb(colors[layer], 0.92);
      ctx.beginPath();
      const base = h * (0.58 + layer * 0.11);
      ctx.moveTo(0, h);
      if (kind === "city") {
        let x = 0; let k = layer * 7 + 3;
        ctx.lineTo(0, base);
        while (x < w) {
          const bw = 40 + ((k * 37) % 70), bh = 30 + ((k * 53) % 120) * (1 - layer * 0.25);
          ctx.lineTo(x, base - bh); ctx.lineTo(x + bw, base - bh); x += bw; ctx.lineTo(x, base - 10); k++;
        }
        ctx.lineTo(w, base);
      } else {
        for (let x = 0; x <= w; x += 8) {
          let y;
          const ph = layer * 1.7;
          if (kind === "waves") y = base + Math.sin(x / 70 + t * (1.2 + layer * 0.4) + ph) * (10 + layer * 6) + Math.sin(x / 23 + t * 2 + ph) * 3;
          else if (kind === "mountains") y = base - 120 * (1 - layer * 0.3) * Math.abs(Math.sin(x / (180 - layer * 30) + ph)) - 30 * Math.sin(x / 47 + ph);
          else if (kind === "dunes") y = base - 40 * Math.sin(x / 210 + ph + t * 0.03) - 14 * Math.sin(x / 90 + ph);
          else y = base - 46 * Math.sin(x / 260 + ph + t * 0.02) - 18 * Math.sin(x / 110 + ph * 2);
          ctx.lineTo(x, y);
        }
      }
      ctx.lineTo(w, h); ctx.closePath(); ctx.fill();
    }
  }

  _particles(t, layer) {
    const ctx = this.ctx, w = this.w, h = this.h;
    const kind = this.motif.particles;
    const half = Math.floor(this.particles.length / 2);
    const list = layer === "back" ? this.particles.slice(0, half) : this.particles.slice(half);
    for (const p of list) {
      let x = p.x, y = p.y;
      if (kind === "stars") {
        y = p.y * 0.6; const a = 0.4 + 0.6 * Math.abs(Math.sin(t * p.s + p.p));
        ctx.fillStyle = `rgba(255,255,240,${a})`; ctx.fillRect(x, y, 1 + p.r * 2, 1 + p.r * 2);
      } else if (kind === "embers") {
        y = (p.y - t * 60 * p.s) % h; if (y < 0) y += h; x = p.x + Math.sin(t + p.p) * 14;
        ctx.fillStyle = `rgba(255,${120 + Math.round(p.r * 100)},40,${0.5 + p.r * 0.5})`;
        ctx.beginPath(); ctx.arc(x, y, 1.5 + p.r * 3, 0, Math.PI * 2); ctx.fill();
      } else if (kind === "bubbles") {
        y = (p.y - t * 25 * p.s) % h; if (y < 0) y += h; x = p.x + Math.sin(t * 0.8 + p.p) * 10;
        ctx.strokeStyle = `rgba(220,245,255,${0.25 + p.r * 0.4})`; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(x, y, 3 + p.r * 8, 0, Math.PI * 2); ctx.stroke();
      } else if (kind === "leaves") {
        y = (p.y + t * 30 * p.s) % h; x = (p.x + Math.sin(t * 0.7 + p.p) * 40 + t * 12) % w;
        ctx.save(); ctx.translate(x, y); ctx.rotate(t * p.s + p.p);
        ctx.fillStyle = `rgba(${90 + Math.round(p.r * 80)},${170 + Math.round(p.r * 60)},90,0.8)`;
        ctx.beginPath(); ctx.ellipse(0, 0, 9 + p.r * 6, 4 + p.r * 2, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      } else if (kind === "swirls") {
        const r = 60 + p.r * 160; const a = t * 0.3 * p.s + p.p;
        ctx.strokeStyle = "rgba(255,255,255,0.12)"; ctx.lineWidth = 2 + p.r * 3;
        ctx.beginPath(); ctx.arc(p.x, p.y * 0.7, r, a, a + 1.4); ctx.stroke();
      } else {
        x = (p.x + t * 10 * p.s) % w; y = p.y + Math.sin(t * 0.5 + p.p) * 12;
        ctx.fillStyle = `rgba(255,250,230,${0.15 + p.r * 0.45})`;
        ctx.beginPath(); ctx.arc(x, y, 1 + p.r * 2.5, 0, Math.PI * 2); ctx.fill();
      }
    }
  }

  _caption() {
    const ctx = this.ctx, w = this.w, h = this.h;
    const pad = 64;
    // Top labels
    ctx.font = "600 22px Outfit, sans-serif";
    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.textBaseline = "top";
    if (this.label) ctx.fillText(this.label, pad, 48);
    if (this.kindLabel) {
      ctx.font = "500 16px Outfit, sans-serif";
      const tw = ctx.measureText(this.kindLabel).width;
      ctx.fillStyle = "rgba(0,0,0,0.35)";
      this._round(w - pad - tw - 24, 46, tw + 24, 30, 15); ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.95)"; ctx.fillText(this.kindLabel, w - pad - tw - 12, 52);
    }
    if (!this.text) return;
    // Caption, revealed word by word in step with the narration
    const words = this.text.split(/\s+/);
    const shown = this.progress >= 1 ? words.length : Math.min(words.length, Math.ceil(this.progress * words.length) + 2);
    const size = this.text.length > 260 ? 26 : this.text.length > 160 ? 30 : 36;
    ctx.font = `400 ${size}px Literata, Georgia, serif`;
    const maxW = w - pad * 2 - 40;
    const lines = [];
    let line = [];
    for (const word of words) {
      const test = [...line, word].join(" ");
      if (ctx.measureText(test).width > maxW && line.length) { lines.push(line); line = [word]; } else line.push(word);
    }
    if (line.length) lines.push(line);
    const lh = size * 1.45;
    const boxH = lines.length * lh + 48;
    const y0 = h - boxH - 44;
    ctx.fillStyle = "rgba(0,0,0,0.42)";
    this._round(pad, y0, w - pad * 2, boxH, 26); ctx.fill();
    let idx = 0;
    ctx.textBaseline = "top";
    lines.forEach((ln, li) => {
      let x = pad + 20 + (maxW - ctx.measureText(ln.join(" ")).width) / 2;
      for (const word of ln) {
        ctx.fillStyle = idx < shown ? "rgba(255,255,255,0.97)" : "rgba(255,255,255,0.28)";
        ctx.fillText(word, x, y0 + 24 + li * lh);
        x += ctx.measureText(word + " ").width;
        idx++;
      }
    });
  }

  _round(x, y, w, h, r) {
    const ctx = this.ctx;
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
}

// Keep a scene in sync with the global player.
export function bindSceneToPlayer(scene, { kindLabel } = {}) {
  const apply = ({ playlist, item }) => {
    if (!playlist || !item) return;
    const kl = kindLabel || (playlist.kind === "scripture" ? `Scripture · ${playlist.subtitle}` :
      playlist.kind === "retell" ? "Retelling · not Scripture text" : playlist.kind === "condensed" ? "Exact verses" : "Answer from your library");
    scene.setSegment({ text: item.intro ? "" : item.text, label: item.label || playlist.title, kindLabel: kl, title: playlist.title,
      motifText: item.motifText || item.text });
  };
  const offs = [
    store.on("player:item", apply),
    store.on("player:progress", (p) => scene.setProgress(p.itemDuration ? p.itemTime / p.itemDuration : 0)),
  ];
  if (player.playlist) apply({ playlist: player.playlist, item: player.current() });
  return () => offs.forEach((f) => f());
}

// Full-screen story theatre with optional video recording.
export function openTheater() {
  if (!player.playlist) { toast("Start a passage or retelling first."); return; }
  const canvas = el("canvas", { "aria-label": "Animated story scene" });
  const scene = new StoryScene(canvas);
  scene.reduceMotion = !!store.settings.reduce_motion;
  const unbind = bindSceneToPlayer(scene);
  scene.start();
  const playBtn = el("button", { class: "btn", onclick: () => player.toggle() }, icon(player.playing ? "pause" : "play"));
  const recBtn = el("button", { class: "btn primary" }, icon("record", 14), "Make a video");
  const status = el("span", { class: "disclaimer" },
    "Decorative visuals: colours and shapes are picked from words in the text (like “sea” or “night”). They don't depict people or events.");
  const bar = el("div", { class: "bar" },
    el("button", { class: "btn", onclick: () => player.prev(), "aria-label": "Previous" }, icon("prev")), playBtn,
    el("button", { class: "btn", onclick: () => player.next(), "aria-label": "Next" }, icon("next")), recBtn, status,
    el("button", { class: "btn", onclick: () => close() }, icon("x"), "Close"));
  const root = el("div", { class: "theater", role: "dialog", "aria-label": "Story view" }, canvas, bar);
  const offState = store.on("player:state", ({ playing }) => { playBtn.replaceChildren(icon(playing ? "pause" : "play")); });
  let recorder = null;
  let chunks = [];
  let offEnded = null;

  recBtn.addEventListener("click", async () => {
    if (recorder) { recorder.stop(); return; }
    const audioStream = player.recordingStream();
    if (!canvas.captureStream || !window.MediaRecorder || !audioStream) {
      toast("Video recording isn't supported by this system's web view.", "err"); return;
    }
    const mime = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"].find((m) => MediaRecorder.isTypeSupported(m));
    if (!mime) { toast("No supported video format for recording.", "err"); return; }
    const stream = new MediaStream([...canvas.captureStream(30).getVideoTracks(), ...audioStream.getAudioTracks()]);
    recorder = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 4_000_000 });
    chunks = [];
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = async () => {
      player.recording = false;
      offEnded && offEnded();
      recBtn.replaceChildren(icon("record", 14), "Make a video");
      const blob = new Blob(chunks, { type: mime.split(";")[0] });
      recorder = null;
      status.textContent = "Saving video…";
      try {
        const name = (player.playlist?.title || "story").replace(/[^\w .-]/g, "");
        const res = await api.raw("POST", `/api/export/video?${api.qs({ name })}`, blob, { "Content-Type": mime.split(";")[0] });
        const j = await res.json();
        status.textContent = `Saved: ${j.path}`;
        toast("Video saved to your Downloads folder.");
      } catch (e) { status.textContent = ""; toast(`Couldn't save the video: ${e.message}`, "err"); }
    };
    player.recording = true;
    offEnded = store.on("player:ended", () => recorder && recorder.state === "recording" && recorder.stop());
    player.pause();
    player.jumpTo(0);
    recorder.start(1000);
    recBtn.replaceChildren(icon("x", 14), "Stop recording");
    status.textContent = "Recording… the video ends when the narration ends.";
    player.play();
  });

  function close() {
    if (recorder) recorder.stop();
    scene.stop(); unbind(); offState(); root.remove(); document.removeEventListener("keydown", onKey);
  }
  const onKey = (e) => { if (e.key === "Escape") close(); if (e.key === " " && e.target === document.body) { e.preventDefault(); player.toggle(); } };
  document.addEventListener("keydown", onKey);
  document.body.append(root);
}

// Audio engine: plays a playlist of short segments (one per verse or sentence),
// each synthesized locally on demand, with a single seekable timeline.
import { api } from "./api.js";
import { store } from "./store.js";
import { toast } from "./ui.js";

const CHARS_PER_SEC = 15; // rough speech rate, used until a clip's real duration is known

export function scripturePlaylist(p, { announce = true } = {}) {
  const src = p.source || {};
  const items = [];
  if (announce) {
    const what = p.whole_chapter ? `${p.book_name}, chapter ${p.chapter}.` : `${p.reference.replace(":", ", verses ").replace(/-/, " to ")}.`;
    items.push({ key: "intro", label: p.reference, text: `${what} ${src.title || ""}.`, intro: true });
  }
  for (const v of p.verses) {
    items.push({ key: `${v.chapter}:${v.verse}`, label: `${p.book_name} ${v.chapter}:${v.verse}`, text: v.text, chapter: v.chapter, verse: v.verse });
  }
  return {
    id: `scripture:${src.id}:${p.reference}`,
    kind: "scripture",
    title: p.reference,
    subtitle: `${src.title || ""}${src.abbreviation ? ` (${src.abbreviation})` : ""}`,
    items,
    meta: { book: p.book, chapter: p.chapter, source_id: src.id, reference: p.reference, next: p.next, whole: p.whole_chapter, bookName: p.book_name },
  };
}

class Player {
  constructor() {
    this.audio = new Audio();
    this.audio.preload = "auto";
    if ("preservesPitch" in this.audio) this.audio.preservesPitch = true;
    this.playlist = null;
    this.index = 0;
    this.playing = false;
    this.clips = new Map(); // key -> {url, duration}
    this.durations = new Map();
    this.loadToken = 0;
    this.rate = 1;
    this.volume = 0.9;
    this.voice = "";
    this.listenedSeconds = 0;
    this.sleep = null;
    this.fadeFactor = 1;
    this.audioCtx = null;
    this._lastTick = performance.now();

    this.audio.addEventListener("ended", () => this._onEnded());
    this.audio.addEventListener("timeupdate", () => this._progress());
    this.audio.addEventListener("loadedmetadata", () => {
      const it = this.current();
      if (it && isFinite(this.audio.duration)) this.durations.set(this._key(it), this.audio.duration);
      this._progress();
    });
    this.audio.addEventListener("error", () => {
      if (this.audio.src) toast("This audio clip couldn't be played.", "err");
    });
    setInterval(() => this._tick(), 500);
    this._mediaSession();
  }

  configure({ rate, volume, voice }) {
    if (rate) this.setRate(rate);
    if (volume !== undefined) this.setVolume(volume);
    if (voice) this.voice = voice;
  }

  current() { return this.playlist ? this.playlist.items[this.index] : null; }
  _key(item, voice = this.voice) { return `${voice}|${item.text}`; }

  estimate(item) { return this.durations.get(this._key(item)) ?? Math.max(1.5, item.text.length / CHARS_PER_SEC + 0.3); }
  totalDuration() { return this.playlist ? this.playlist.items.reduce((s, it) => s + this.estimate(it), 0) : 0; }
  offsetOf(i) { let s = 0; for (let k = 0; k < i; k++) s += this.estimate(this.playlist.items[k]); return s; }
  globalTime() { return this.playlist ? this.offsetOf(this.index) + (this.audio.currentTime || 0) : 0; }

  load(playlist, { start = 0, autoplay = true } = {}) {
    this._logHistory(false);
    this.playlist = playlist;
    this.index = Math.max(0, Math.min(start, playlist.items.length - 1));
    this.listenedSeconds = 0;
    this.audio.pause();
    this.audio.removeAttribute("src");
    store.emit("player:load", playlist);
    store.emit("player:item", { playlist, index: this.index, item: this.current() });
    this._updateMediaSession();
    if (autoplay) this.play(); else this._progress();
  }

  async play() {
    if (!this.playlist) return;
    if (!this.voice) { toast("Choose a voice first (Voices).", "err"); return; }
    this.playing = true;
    store.emit("player:state", { playing: true });
    if (this.audio.src && this.audio.dataset.key === this._key(this.current())) {
      try { await this.audio.play(); } catch (e) { this._playFailed(e); }
    } else {
      await this._playIndex(this.index, 0);
    }
  }

  pause() {
    this.playing = false;
    this.audio.pause();
    store.emit("player:state", { playing: false });
  }

  toggle() { this.playing ? this.pause() : this.play(); }
  next() { if (this.playlist && this.index < this.playlist.items.length - 1) this.jumpTo(this.index + 1); }
  prev() {
    if (!this.playlist) return;
    if (this.audio.currentTime > 2.5 || this.index === 0) this.jumpTo(this.index, 0);
    else this.jumpTo(this.index - 1);
  }
  jumpTo(i, offset = 0) {
    if (!this.playlist) return;
    this.index = Math.max(0, Math.min(i, this.playlist.items.length - 1));
    store.emit("player:item", { playlist: this.playlist, index: this.index, item: this.current() });
    if (this.playing) this._playIndex(this.index, offset);
    else { this.audio.removeAttribute("src"); this._pendingOffset = offset; this._progress(); }
  }
  seekTo(seconds) {
    if (!this.playlist) return;
    let acc = 0;
    for (let i = 0; i < this.playlist.items.length; i++) {
      const d = this.estimate(this.playlist.items[i]);
      if (seconds < acc + d || i === this.playlist.items.length - 1) {
        if (i === this.index && this.audio.src) { this.audio.currentTime = Math.max(0, seconds - acc); this._progress(); }
        else this.jumpTo(i, Math.max(0, seconds - acc));
        return;
      }
      acc += d;
    }
  }
  setRate(r) { this.rate = Number(r) || 1; this.audio.playbackRate = this.rate; store.emit("player:rate", this.rate); }
  setVolume(v) { this.volume = Math.max(0, Math.min(1, Number(v))); this._applyVolume(); }
  _applyVolume() { this.audio.volume = Math.max(0, Math.min(1, this.volume * this.fadeFactor)); }
  setVoice(id) {
    if (id === this.voice) return;
    this.voice = id;
    store.emit("player:voice", id);
    if (this.playlist && this.playing) this._playIndex(this.index, 0); // restart the current verse in the new voice
    else this.audio.removeAttribute("src");
  }

  async clip(item, voice = this.voice) {
    const key = this._key(item, voice);
    if (this.clips.has(key)) return this.clips.get(key);
    const promise = (async () => {
      const res = await api.raw("POST", "/api/tts", { voice, text: item.text });
      const blob = await res.blob();
      const duration = parseFloat(res.headers.get("X-Duration")) || null;
      const url = URL.createObjectURL(blob);
      if (duration) this.durations.set(key, duration);
      return { url, duration, blob };
    })();
    this.clips.set(key, promise);
    promise.catch(() => this.clips.delete(key));
    if (this.clips.size > 160) { // drop the oldest clips
      const [oldKey, old] = this.clips.entries().next().value;
      this.clips.delete(oldKey);
      Promise.resolve(old).then((c) => c && URL.revokeObjectURL(c.url)).catch(() => {});
    }
    return promise;
  }

  async _playIndex(i, offset) {
    const token = ++this.loadToken;
    const item = this.playlist.items[i];
    store.emit("player:buffering", true);
    let c;
    try {
      c = await this.clip(item);
    } catch (e) {
      store.emit("player:buffering", false);
      if (token === this.loadToken) { this.pause(); toast(e.message || "Speech synthesis failed.", "err"); }
      return;
    }
    if (token !== this.loadToken) return;
    store.emit("player:buffering", false);
    this.audio.src = c.url;
    this.audio.dataset.key = this._key(item);
    this.audio.playbackRate = this.rate;
    this._applyVolume();
    const startAt = offset || this._pendingOffset || 0;
    this._pendingOffset = 0;
    if (startAt) {
      await new Promise((r) => { this.audio.addEventListener("loadedmetadata", r, { once: true }); setTimeout(r, 800); });
      try { this.audio.currentTime = startAt; } catch { /* ignore */ }
    }
    if (this.playing) {
      try { await this.audio.play(); } catch (e) { this._playFailed(e); }
    }
    for (const k of [1, 2]) {
      const nxt = this.playlist.items[i + k];
      if (nxt) this.clip(nxt).catch(() => {});
    }
  }

  _playFailed(e) {
    if (e && e.name === "AbortError") return;
    this.playing = false;
    store.emit("player:state", { playing: false });
  }

  async _onEnded() {
    if (!this.playlist) return;
    if (this.index < this.playlist.items.length - 1) {
      this.index += 1;
      store.emit("player:item", { playlist: this.playlist, index: this.index, item: this.current() });
      this._playIndex(this.index, 0);
      return;
    }
    // End of playlist
    this._logHistory(true);
    store.emit("player:ended", this.playlist);
    const meta = this.playlist.meta || {};
    const chapterSleep = this.sleep && this.sleep.mode === "chapter";
    if (chapterSleep) { this.cancelSleep(); this.pause(); store.emit("sleep:done"); return; }
    if (this.playlist.kind === "scripture" && meta.next && store.settings.auto_continue && meta.whole && !this.recording) {
      try {
        const p = await api.get(`/api/passage?${api.qs({ ref: meta.next, source_id: meta.source_id })}`);
        const pl = scripturePlaylist(p, { announce: store.settings.announce_passage });
        store.emit("player:autocontinue", p);
        this.load(pl, { autoplay: true });
        return;
      } catch (e) { toast(`Auto mode stopped: ${e.message}`, "err"); }
    }
    this.pause();
    this.audio.removeAttribute("src");
    this.index = 0;
  }

  _progress() {
    if (!this.playlist) return;
    store.emit("player:progress", { index: this.index, time: this.globalTime(), total: this.totalDuration(),
      itemTime: this.audio.currentTime || 0, itemDuration: this.estimate(this.current()) });
  }

  _tick() {
    const now = performance.now();
    if (this.playing && !this.audio.paused) this.listenedSeconds += (now - this._lastTick) / 1000;
    this._lastTick = now;
    if (this.sleep && this.sleep.mode === "minutes") {
      const remaining = (this.sleep.endsAt - Date.now()) / 1000;
      const fade = Number(store.settings.sleep_fade_seconds || 60);
      this.fadeFactor = remaining < fade ? Math.max(0, remaining / fade) : 1;
      this._applyVolume();
      store.emit("sleep:tick", { remaining, mode: "minutes" });
      if (remaining <= 0) {
        this.cancelSleep();
        this.pause();
        store.emit("sleep:done");
      }
    }
  }

  setSleep(mode, minutes = 30) {
    if (mode === "minutes") this.sleep = { mode, endsAt: Date.now() + minutes * 60000, minutes };
    else if (mode === "chapter") this.sleep = { mode };
    else this.sleep = null;
    this.fadeFactor = 1;
    this._applyVolume();
    store.emit("sleep:changed", this.sleep);
  }
  cancelSleep() { this.sleep = null; this.fadeFactor = 1; this._applyVolume(); store.emit("sleep:changed", null); }

  _logHistory(completed) {
    const pl = this.playlist;
    if (!pl || pl.kind !== "scripture" || !pl.meta || (!completed && this.listenedSeconds < 20)) return;
    api.post("/api/history", { book: pl.meta.book, chapter: pl.meta.chapter, source_id: pl.meta.source_id, mode: "listen",
      seconds: Math.round(this.listenedSeconds), completed }).catch(() => {});
    this.listenedSeconds = 0;
  }

  // Route audio through Web Audio so it can be recorded together with the story canvas.
  recordingStream() {
    if (!this.audioCtx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return null;
      this.audioCtx = new Ctx();
      this.mediaSource = this.audioCtx.createMediaElementSource(this.audio);
      this.recDest = this.audioCtx.createMediaStreamDestination();
      this.mediaSource.connect(this.audioCtx.destination);
      this.mediaSource.connect(this.recDest);
    }
    if (this.audioCtx.state === "suspended") this.audioCtx.resume();
    return this.recDest.stream;
  }

  _mediaSession() {
    if (!("mediaSession" in navigator)) return;
    const ms = navigator.mediaSession;
    try {
      ms.setActionHandler("play", () => this.play());
      ms.setActionHandler("pause", () => this.pause());
      ms.setActionHandler("previoustrack", () => this.prev());
      ms.setActionHandler("nexttrack", () => this.next());
    } catch { /* unsupported actions */ }
  }
  _updateMediaSession() {
    if (!("mediaSession" in navigator) || !this.playlist || !window.MediaMetadata) return;
    navigator.mediaSession.metadata = new MediaMetadata({ title: this.playlist.title, artist: this.playlist.subtitle, album: "Bible Narrator" });
  }
}

export const player = new Player();

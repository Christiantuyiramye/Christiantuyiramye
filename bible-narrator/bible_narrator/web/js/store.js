// Shared app state + a tiny event bus.
import { api } from "./api.js";

const listeners = new Map();

export const store = {
  settings: {},
  status: null,
  voices: [],
  sources: [],

  on(evt, fn) {
    if (!listeners.has(evt)) listeners.set(evt, new Set());
    listeners.get(evt).add(fn);
    return () => listeners.get(evt).delete(fn);
  },
  emit(evt, data) { (listeners.get(evt) || []).forEach((fn) => { try { fn(data); } catch (e) { console.error(e); } }); },

  async refreshStatus() {
    this.status = await api.get("/api/status");
    this.settings = this.status.settings;
    this.emit("status", this.status);
    return this.status;
  },
  async refreshVoices() {
    const r = await api.get("/api/voices");
    this.voices = r.voices;
    this.emit("voices", r);
    return r;
  },
  async refreshSources() {
    const r = await api.get("/api/sources");
    this.sources = r.sources;
    this.emit("sources", r);
    return r;
  },
  async saveSettings(values) {
    this.settings = await api.put("/api/settings", values);
    this.emit("settings", this.settings);
    return this.settings;
  },
  bibles() { return this.sources.filter((s) => s.kind === "scripture"); },
  translationId() {
    const pref = Number(this.settings.default_translation);
    const bibles = this.bibles();
    if (pref && bibles.some((b) => b.id === pref)) return pref;
    return (bibles.find((b) => b.enabled) || bibles[0] || {}).id;
  },
  voiceLabel(id) {
    const v = this.voices.find((x) => x.id === id);
    return v ? v.label : id;
  },
  modelReady() {
    const s = this.status && this.status.llm;
    return !!s && ["ready", "idle", "loading"].includes(s.state);
  },
};

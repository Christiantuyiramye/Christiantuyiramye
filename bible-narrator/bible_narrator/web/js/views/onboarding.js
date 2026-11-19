// First-run guide: privacy, library, voices, language model.
import { store } from "../store.js";
import { el, icon, modal } from "../ui.js";
import { kokoroCard, previewVoice } from "./voices.js";
import { modelSection } from "./settings.js";

export function openOnboarding() {
  let step = 0;
  const body = el("div");
  const steps = el("div", { class: "steps" });
  const back = el("button", { class: "btn" }, "Back");
  const next = el("button", { class: "btn primary big" }, "Continue");
  const m = modal(el("div", {}, steps, body, el("div", { class: "spread", style: { marginTop: "22px" } }, back, next)), { wide: true, dismissable: false });

  const pages = [
    () => el("div", { class: "stack" },
      el("div", { class: "eyebrow" }, "Welcome"),
      el("h1", {}, "Bible Narrator"),
      el("p", { class: "muted", style: { fontSize: "16px" } }, "Listen to Scripture, hear faithful retellings, and ask questions answered from your own library."),
      el("div", { class: "notice" }, icon("shield"), el("span", {}, el("b", {}, "Private by design. "), "Everything runs on this computer: no accounts, analytics, telemetry or cloud AI. The internet is used only if you choose to download a voice or model.")),
      el("div", { class: "notice" }, icon("info"), el("span", {}, el("b", {}, "Honest answers. "), "Answers come only from your library, with citations. When your library doesn't support an answer, the app says so. Scripture is always labeled separately from commentary."))),
    () => {
      const bibles = store.bibles();
      const sel = el("select", { class: "input" }, ...bibles.map((b) => el("option", { value: b.id }, `${b.title} (${b.abbreviation}) — ${b.license}`)));
      sel.value = String(store.translationId() || "");
      sel.onchange = () => store.saveSettings({ default_translation: sel.value });
      return el("div", { class: "stack" },
        el("div", { class: "eyebrow" }, "Step 1 · Library"), el("h2", {}, "Your Bible library is ready"),
        el("p", { class: "muted" }, `${store.sources.length} public-domain texts were installed and work offline:`),
        el("ul", {}, ...store.sources.map((s) => el("li", {}, `${s.title} — ${s.kind_label} · ${s.license}`))),
        el("label", { class: "field" }, el("span", {}, "Default translation"), sel),
        el("p", { class: "small muted" }, "You can add more Bibles, commentaries and dictionaries you have the right to use from the Library at any time."));
    },
    () => {
      const wrap = el("div", { class: "stack" }, el("div", { class: "eyebrow" }, "Step 2 · Voices"), el("h2", {}, "Choose how it sounds"));
      const basic = store.voices.filter((v) => v.engine === "espeak").slice(0, 4);
      wrap.append(el("p", { class: "muted" }, `${store.voices.length} voices are installed now. Basic voices work immediately; natural voices need a one-time ~100 MB download (or files you copy in).`));
      kokoroCard(() => go(step)).then((c) => wrap.append(c, el("div", { class: "row wrap" }, el("span", { class: "small muted" }, "Preview:"),
        ...[...store.voices.filter((v) => v.engine === "kokoro").slice(0, 4), ...basic].map((v) => {
          const b = el("button", { class: "chip" }, icon("play", 12), v.label);
          b.onclick = () => previewVoice(v.id);
          return b;
        }))));
      return wrap;
    },
    () => {
      const wrap = el("div", { class: "stack" }, el("div", { class: "eyebrow" }, "Step 3 · AI model"), el("h2", {}, "Add a local language model (optional)"),
        el("p", { class: "muted" }, "Retell and Ask use an open-weight model that runs on your computer. Without one, Read Scripture, narration, library search and a “condensed reading” of key verses still work."));
      modelSection().then((s) => wrap.append(s));
      return wrap;
    },
    () => el("div", { class: "stack" },
      el("div", { class: "eyebrow" }, "All set"), el("h1", {}, "Ready when you are"),
      el("p", { class: "muted" }, "Tip: press Space to play or pause, ← → to move between verses. Use Sleep mode from the player's moon button.")),
  ];

  function go(i) {
    step = Math.max(0, Math.min(pages.length - 1, i));
    steps.replaceChildren(...pages.map((_, k) => el("i", { class: k <= step ? "on" : "" })));
    body.replaceChildren(pages[step]());
    back.style.visibility = step === 0 ? "hidden" : "visible";
    next.textContent = step === pages.length - 1 ? "Start" : step === 3 && !store.modelReady() ? "Skip for now" : "Continue";
  }
  back.onclick = () => go(step - 1);
  next.onclick = async () => {
    if (step === pages.length - 1) {
      await store.saveSettings({ onboarding_complete: true });
      await store.refreshVoices();
      m.close();
      window.bnNavigate("home");
    } else go(step + 1);
  };
  go(0);
}

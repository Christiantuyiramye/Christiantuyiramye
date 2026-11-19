// Sleep mode: a sleep timer that fades the voice out, plus a dim, calm screen.
import { player } from "./player.js";
import { store } from "./store.js";
import { el, fmtTime, icon, modal, toast } from "./ui.js";

export function openSleepMode() {
  const minutes = Number(store.settings.sleep_minutes || 30);
  let choice = player.sleep ? player.sleep.mode : "minutes";
  let mins = player.sleep && player.sleep.minutes ? player.sleep.minutes : minutes;
  const opts = [15, 30, 45, 60, 90];
  const content = el("div", { class: "stack" },
    el("div", { class: "eyebrow" }, "Sleep mode"),
    el("h2", {}, "Fall asleep to Scripture"),
    el("p", { class: "muted" }, "The voice gently fades out at the end, and the screen dims. Auto mode keeps reading chapter after chapter until the timer ends."),
  );
  const grid = el("div", { class: "chapters", style: { gridTemplateColumns: "repeat(6, 1fr)" } });
  const render = () => {
    grid.replaceChildren(
      ...opts.map((m) => el("button", { class: choice === "minutes" && mins === m ? "on" : "", onclick: () => { choice = "minutes"; mins = m; render(); } }, `${m}m`)),
      el("button", { class: choice === "chapter" ? "on" : "", title: "Stop at the end of this chapter", onclick: () => { choice = "chapter"; render(); } }, "Chapter"),
    );
  };
  render();
  const startBtn = el("button", { class: "btn primary big" }, icon("moon"), "Start sleep mode");
  const offBtn = el("button", { class: "btn" }, "Turn off timer");
  content.append(grid, el("div", { class: "row wrap" }, startBtn, player.sleep ? offBtn : null));
  if (!player.playlist) content.append(el("div", { class: "notice warn" }, icon("info"), "Pick a chapter in Read Scripture first — sleep mode plays whatever is loaded in the player."));
  const m = modal(content);
  offBtn.onclick = () => { player.cancelSleep(); m.close(); toast("Sleep timer off."); };
  startBtn.onclick = () => {
    if (!player.playlist) { toast("Choose something to listen to first.", "err"); return; }
    player.setSleep(choice, mins);
    if (choice === "minutes") store.saveSettings({ sleep_minutes: mins });
    m.close();
    if (!player.playing) player.play();
    showSleepScreen();
  };
}

function showSleepScreen() {
  const clock = el("div", { class: "clock" }, "");
  const line = el("div", { class: "verse-line" }, "");
  const hint = el("div", { class: "small" }, "Click anywhere or press Esc to return. The timer keeps running.");
  const root = el("div", { class: "sleep-overlay", role: "dialog", "aria-label": "Sleep mode" },
    el("div", {}, el("div", { class: "moon" }), clock, line, hint));
  const offs = [
    store.on("sleep:tick", ({ remaining }) => { clock.textContent = fmtTime(remaining); }),
    store.on("player:item", ({ item }) => { line.textContent = item && !item.intro ? item.text : ""; }),
    store.on("sleep:done", () => { clock.textContent = "Good night"; line.textContent = ""; }),
  ];
  if (player.sleep && player.sleep.mode === "chapter") clock.textContent = "End of chapter";
  const it = player.current();
  if (it && !it.intro) line.textContent = it.text;
  const close = () => { offs.forEach((f) => f()); root.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  root.addEventListener("click", close);
  document.addEventListener("keydown", onKey);
  document.body.append(root);
}

# DECISIONS.md — Simple Word

Running record of every architectural and product decision, with reasons.
Newest entries at the bottom of each section.

---

## Open questions for the owner (§12 of the brief)

These were required to be confirmed before writing code. This session ran
autonomously, so each has a **proposed default** recorded here. Work done in
Phase 0 (content pipeline) does not depend on any of them; **please confirm
or change each one before Phase 1 begins.**

| # | Question | Proposed default | Status |
|---|---|---|---|
| 1 | App name | Working title **"Simple Word"** (subtitle carrying "Bible"), application ID `com.christiantuyiramye.simpleword` | ⏳ awaiting owner |
| 2 | Free or paid | **Free, no IAP, no ads.** Simplest licensing posture and truest to "personal first" | ⏳ awaiting owner |
| 3 | Solo or family sharing | **Solo** — single-user data, private sync only | ⏳ awaiting owner |
| 4 | Monthly review generation | **Deterministic Part 1 + bundled question bank** first; generated questions later behind the `ReviewGenerator` interface | ⏳ awaiting owner |
| 5 | Liturgical tradition | **Broadly Protestant/evangelical**, exactly as structured in the brief §F6 | ⏳ awaiting owner |
| 6 | ~~Xcode + Mac availability~~ | **Resolved by D-011**: owner has a Windows desktop and an Android phone, no Mac. Platform pivoted to Flutter; no Xcode needed | ✅ resolved 2026-08-01 |
| 7 | Language | **English only in v1.** Kinyarwanda/Swahili sourcing not started | ⏳ awaiting owner |

---

## Phase 0 — Content pipeline

### D-001: Build environment and source acquisition
The pipeline was developed in a sandboxed cloud environment whose network
policy only allows `raw.githubusercontent.com` and `git clone` of public
GitHub repositories. `ebible.org`, `ccel.org`, `gutenberg.org`, and
`openhymnal.org` are unreachable from the sandbox. All sources were therefore
taken from well-maintained GitHub mirrors, each verified for licence and
data quality (see CREDITS.md). `fetch_sources.py` records every URL and can
re-download everything on any machine.

### D-002: Translations bundled
BBE (default), WEB, BSB, KJV — per the brief. Notes:
- BBE, BSB, KJV come from `scrollmapper/bible_databases` (cleaned JSON).
- WEB comes from `TehShrike/world-english-bible` because scrollmapper's 2025
  branch does not carry the WEB. This is the **American WEB edition, which
  renders the divine name as "Yahweh"** in the Old Testament. If "LORD" is
  preferred, the British/Messianic editions (WEBBE) exist — swapping is a
  pipeline change only. Flagging for the owner's theological judgement.
- All four aligned to the shared 66-book canon with KJV-style versification;
  the integrity script verifies chapter counts exactly and per-chapter verse
  counts within ±3 of the KJV.

### D-003: Cross-references are CC-BY, not pure public domain
The brief (§2.2) asks for the Treasury of Scripture Knowledge. What is
bundled is **openbible.info's cross-reference dataset (CC Attribution
licence, TSK-derived and expanded, with helpfulness votes)** — this is
plainly what the brief's schema anticipated, since it has the `votes`
column. CC-BY permits free redistribution with attribution; attribution is
recorded in CREDITS.md and must appear in the in-app Credits screen.
**Flag: if the owner wants pure public domain only, we swap in raw TSK and
lose the votes ranking.**

### D-004: Commentary CUT from Phase 0 (blocked, not abandoned)
No faithful, structured public-domain copy of Matthew Henry's Concise
Commentary (or JFB/Barnes) could be located on any reachable host. CCEL,
which hosts the canonical ThML XML, is blocked by the sandbox network
policy. Decisions:
- The `commentary` table ships in the schema, empty. The integrity script
  treats an empty table as a warning, and fully validates it once populated.
- Population is scheduled for Phase 4 (study layer), which is where
  commentary is first needed. Options then: run the fetch on the owner's
  Mac against CCEL's ThML, or widen the sandbox network policy.
- Per §13 ("do not resolve licensing ambiguity by guessing") nothing was
  scraped from unverifiable re-hosts.

### D-005: Hymnal source and known exclusions
Hymns come from the **Open Hymnal Project** (explicitly public-domain,
curated for licence correctness by that project), via the `mzealey/openhymnal`
mirror: 286 hymns with author, year, meter, and scripture links. Notes:
- **"How Great Thou Art" is deliberately absent**: the familiar English text
  is © Stuart K. Hine (1949) and administered commercially. The brief listed
  it as a priority hymn; it cannot be bundled. It can be added as an
  *external song* (deep link out) instead.
- "Great Is Thy Faithfulness" (1923, US public domain since 2019) is not in
  the Open Hymnal corpus; candidate for a hand-added entry later, with its
  licence note recorded when added.
- Lyrics are reconstructed from the ABC score lyric lines (syllable
  de-hyphenation, verse de-interleaving, trailing-refrain detection). A
  hand-checked override file (`data/hymn_overrides.json`) corrects hymns the
  automatic parse cannot reconstruct faithfully; "It Is Well With My Soul"
  is the first entry. 3 of 289 hymns (refrain-first structures) are skipped
  outright. **Owner review of high-use hymn texts is on the Phase 6 list.**
- One hymn scripture reference in the source data is a typo
  ("1Thess 6:17"); the build drops unresolvable refs rather than shipping a
  broken link.

### D-006: Schema extensions beyond the brief §4.1
- `hymns.scripture_refs` (JSON array of stable refs) — the brief's F7 wants
  hymn→passage links but §4.1 had no column for them.
- `verse_of_the_day(day_index, verse_ref)` — F5 requires a curated bundled
  list; it needs to live somewhere queryable. 147 curated refs, all
  validated to resolve.
- `verses_fts` uses the `porter unicode61` tokenizer so "believes" matches
  "believe"; content-linked to `verses` to halve the index size.

### D-007: Artifacts not committed to git
`content/sources/` (~60 MB of raw downloads) and `content/output/bible.sqlite`
(46 MB) are gitignored. The build is deterministic from
`fetch_sources.py` + `build.py` + `data/`; committing binaries would bloat
the repo toward GitHub's limits for no benefit. The Xcode project will copy
`bible.sqlite` into the app bundle as a build resource in Phase 1.

### D-008: Dictionary entry counts
Easton's 3,962 entries, Smith's 4,488 (of 4,561 in the source — 73 entries
with empty bodies after parsing are dropped rather than shipped blank).
Both public domain (1897/1863), parsed from CCEL ThML via
`neuu-org/bible-dictionary-dataset`.

### D-009: Cross-reference resolution policy
Of 344,799 source rows: 344,143 inserted; 1 dropped for an unresolvable
"from" verse; 655 dropped for unresolvable targets (mostly apocrypha-range
or versification-edge refs). Range ends that overrun a chapter are clamped
to the chapter's last verse. The integrity script proves every shipped row
resolves against the default translation.

### D-010: Reading plans generated, not authored
The four bundled plans are generated deterministically from the canon
(contiguous chapters, even day-sizing). The integrity script verifies each
plan's coverage claim exactly (John 21/21, Psalms 150/150, complete NT,
complete Bible).

---

## Platform pivot

### D-011: Target platform is Flutter (Android + Windows), not iOS
**Date:** 2026-08-01. **Decided by:** owner (Christian), confirming the
recommended option.

The original brief targeted iOS/SwiftUI, but the owner's actual devices are
an **Android phone and a Windows desktop** — no Mac, no iPhone. Xcode
requires a Mac, so the iOS plan was unbuildable, and "personal first" means
the app must live on the owner's own devices. Chosen: **Flutter**, one
codebase shipping to Android (primary, daily use) and Windows desktop
(secondary), with an iOS path preserved for the future if Apple hardware
ever arrives.

Consequences (technology mapping from the brief §3):
- SwiftUI → Flutter widgets; MVVM stays (view models as `ChangeNotifier`/
  streams, repository layer unchanged in spirit).
- SwiftData → **Drift or raw sqlite3** for user data; `bible.sqlite` is
  bundled read-only exactly as built in Phase 0 (`sqlite3` package,
  FFI-based, works identically on Android/Windows/Linux — and in tests).
- CloudKit sync → **deferred**. v1 is fully on-device with a local
  export/backup file. A cross-device sync solution (e.g. user's own Google
  Drive backup) is a later, opt-in decision — nothing phones home.
- AVSpeechSynthesizer → platform TTS via `flutter_tts` (Android natively;
  Windows SAPI).
- WidgetKit → Android home-screen widget (`home_widget`) in the habit
  phase; no Windows equivalent.
- Local notifications → `flutter_local_notifications`.
- App Store checklist (§10) → Google Play (one-time $25) + Windows
  distribution (Microsoft Store or direct installer). Same content-licence
  diligence applies.
- The brief's dependency rule ("none by default; justify every package in
  writing") continues: each Flutter package added is recorded here with its
  reason.

Phase 0 output is unaffected: `bible.sqlite` is platform-neutral by design.

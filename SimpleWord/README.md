# Simple Word

A simple-English Bible app for iOS: reader, narrator, study layer, daily
habit engine, weekly Sunday-service planner, and a monthly review that
tests what was actually read. Built personal-first — fast, fully offline,
no account, no ads, no shame mechanics.

Working title "Simple Word" — final name pending owner decision
(DECISIONS.md, question 1).

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Content pipeline → verified `bible.sqlite` | ✅ **Done** — integrity sweep passes with 0 errors (commentary deferred, see DECISIONS.md D-004) |
| 1 | Reader + search + navigation | Not started — blocked on owner answers to §12 questions and Mac/Xcode confirmation |
| 2–8 | Narrator → habit engine → study → Sunday service → songs → monthly review → ship | Not started |

## Repository layout

```
SimpleWord/
├── README.md        # this file
├── DECISIONS.md     # every architectural/product decision + open questions
├── CREDITS.md       # licence record for every bundled text
└── content/         # Phase 0: the bible.sqlite build pipeline
```

## Key constraints (from the project brief)

- Only public-domain / freely licensed translations ship: BBE (default),
  WEB, BSB, KJV. No modern copyrighted translations, ever.
- The app never displays generated text as scripture; every verse shown is
  retrieved from the local database by reference.
- All user data stays on-device (SwiftData), syncing only to the user's own
  iCloud private database. No analytics, no third-party servers, no API
  keys in the binary.

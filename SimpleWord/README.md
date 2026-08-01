# Simple Word

A simple-English Bible app for **Android and Windows** (Flutter): reader,
narrator, study layer, daily habit engine, weekly Sunday-service planner,
and a monthly review that tests what was actually read. Built
personal-first — fast, fully offline, no account, no ads, no shame
mechanics. (Originally planned for iOS; re-targeted to the owner's actual
devices — see DECISIONS.md D-011.)

Working title "Simple Word" — final name pending owner decision
(DECISIONS.md, question 1).

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Content pipeline → verified `bible.sqlite` | ✅ **Done** — integrity sweep passes with 0 errors (commentary deferred, see DECISIONS.md D-004) |
| 1 | Reader + search + navigation (Flutter) | 🔨 **In progress** — working skeleton: reader with 4 themes and 7 font steps, book/chapter picker, reference-parsing search over FTS5, continue-reading; `flutter analyze` clean, 23 tests green |
| 2–8 | Narrator → habit engine → study → Sunday service → songs → monthly review → ship | Not started |

## Repository layout

```
SimpleWord/
├── README.md        # this file
├── DECISIONS.md     # every architectural/product decision + open questions
├── CREDITS.md       # licence record for every bundled text
├── content/         # Phase 0: the bible.sqlite build pipeline
└── app/             # the Flutter app (Android + Windows; lib/src/...)
```

## Building the app

```sh
# 1. Build the database (once, or after content changes)
cd content && python3 fetch_sources.py && python3 build.py && python3 integrity_check.py
cp output/bible.sqlite ../app/assets/

# 2. Run checks and the app
cd ../app
flutter analyze && flutter test
flutter run                    # Android device/emulator, or -d windows
```

## Key constraints (from the project brief)

- Only public-domain / freely licensed translations ship: BBE (default),
  WEB, BSB, KJV. No modern copyrighted translations, ever.
- The app never displays generated text as scripture; every verse shown is
  retrieved from the local database by reference.
- All user data stays on-device. No analytics, no third-party servers, no API
  keys in the binary.

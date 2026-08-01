# Credits & Licences

Every text bundled in Simple Word, with its source and licence. This file
must remain reachable from the app's Settings screen (brief §2.3, §10).

## Bible translations

| Translation | Licence | Source |
|---|---|---|
| Bible in Basic English (BBE), 1949/1964 | Public domain | [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) |
| World English Bible (WEB) | Public domain (dedicated by its creators; "World English Bible" is a trademark of eBible.org) | [TehShrike/world-english-bible](https://github.com/TehShrike/world-english-bible), original text from [ebible.org](https://ebible.org) |
| Berean Standard Bible (BSB), 2023 | Public domain (CC0 dedication, April 2023) | [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases), original from [berean.bible](https://berean.bible) |
| King James Version (KJV), 1769 | Public domain in the United States (Crown letters patent apply in the UK) | [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) |

## Study material

| Work | Licence | Source |
|---|---|---|
| Cross references (Treasury of Scripture Knowledge, expanded) | **Creative Commons Attribution (CC-BY)** — attribution required: "Cross-reference data from [OpenBible.info](https://www.openbible.info/labs/cross-references/), CC-BY" | openbible.info dataset, mirrored in [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) |
| Easton's Bible Dictionary (M. G. Easton, 1897) | Public domain | [neuu-org/bible-dictionary-dataset](https://github.com/neuu-org/bible-dictionary-dataset), parsed from CCEL ThML |
| Smith's Bible Dictionary (William Smith, 1863) | Public domain | [neuu-org/bible-dictionary-dataset](https://github.com/neuu-org/bible-dictionary-dataset), parsed from CCEL ThML |
| Matthew Henry's Concise Commentary | Public domain — **not yet bundled** (see DECISIONS.md D-004) | planned: [CCEL](https://www.ccel.org/ccel/henry/mhcc.html) |

## Hymns

All 286 bundled hymn texts come from the **Open Hymnal Project**
([openhymnal.org](http://openhymnal.org), 2013/2014 edition, via the
[mzealey/openhymnal](https://github.com/mzealey/openhymnal) mirror). The
Open Hymnal Project publishes only public-domain or freely distributable
hymns and verifies copyright status before inclusion. Per-hymn author,
year, and meter are stored in the database (`hymns` table); every row
carries the licence string "Public Domain (Open Hymnal Project,
openhymnal.org)".

Deliberately **not** bundled (still under copyright):

- "How Great Thou Art" — English text © Stuart K. Hine, 1949.
- All contemporary gospel/CCM works. These may only be added by the user as
  external songs (title + artist + link out to Apple Music / Spotify /
  YouTube); the app never stores or plays their audio or lyrics.

## Audio

No audio recordings are bundled in this phase. Narration is produced
on-device by Apple's speech synthesiser. Any future bundled recordings will
be listed here individually with source and licence before shipping.

## Curated in-repo data

Liturgy templates, the verse-of-the-day reference list, reading-plan
definitions, and hymn override texts are original to this repository
(`SimpleWord/content/data/`) and carry the repository's licence.

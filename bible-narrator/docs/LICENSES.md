# Content, model, voice and software licenses

Bible Narrator's own source code is released under the **MIT License** (`LICENSE`). Everything below is third-party material: it keeps its own license, and the app shows the license of each library source in the Library and Read screens.

## Bundled texts (in `bible_narrator/data/starter/`)

| Text | Status | Notes |
|---|---|---|
| **Berean Standard Bible (BSB)** | **CC0 1.0** (public-domain dedication, April 2023) | Text from [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) `formats/json/BSB.json`. Section headings and footnotes are not included. 31,086 verses: verses that modern critical texts omit (e.g. Matthew 17:21) are absent. |
| **King James Version (KJV), 1769** | **Public domain** in most countries | In the **United Kingdom**, the KJV is under Crown letters patent held by Cambridge University Press. If you distribute this app in the UK, remove the KJV or obtain permission. The text comes from the CrossWire module via scrollmapper, with Strong's tags removed. (Scrollmapper labels its compilation "GPL"; the underlying 1769 text is public domain.) |
| **American Standard Version (ASV), 1901** | **Public domain** | Via scrollmapper. |
| **Easton's Bible Dictionary**, M. G. Easton, 3rd ed. (1897) | Text **public domain**. Digital edition **CC BY-SA 4.0** | Entries from the [Theographic Bible Metadata](https://github.com/robertrouse/theographic-bible-metadata) project by Robert Rouse (viz.bible), converted to plain text. Attribution: "Easton's Bible Dictionary (1897), digitised by Theographic Bible Metadata, CC BY-SA 4.0". The converted file `easton.json.gz` is shared under the same license. It is a 19th-century reference work reflecting its author's views; it is **not Scripture**. |

These files were fetched once, by explicit URL, when the app was built (see `scripts/build_starter_content.py`). The app itself never downloads content on its own.

**Content you import** stays your responsibility. Import only material that is public domain, openly licensed, or licensed to you. The import form requires confirming this and records the license and attribution you enter.

## Voices

| Engine | License | Notes |
|---|---|---|
| **Kokoro-82M** (hexgrad), ONNX export by onnx-community | **Apache-2.0** (model and voice style vectors) | Not bundled; downloaded on request (~100 MB) or supplied by the user. 27 English voices are listed (American and British, female and male), with quality grades from the model card. The novelty "Santa" voice is hidden. |
| **kokoro-onnx** (thewh1teagle) | MIT | Python runtime for Kokoro. |
| **eSpeak NG** (bundled via `espeakng-loader`) | **GPL-3.0-or-later** | Provides the 10 basic voices and Kokoro's phonemizer. Because binary installers include it, **distributed installers must comply with GPL-3.0**: provide the source code (this repository) and the license text. |
| **phonemizer** | GPL-3.0 | Used by kokoro-onnx (same obligation as above). |

None of the voices imitate a real person or another app's proprietary voices.

## Language models

No model is bundled. The catalog offered in the app (all **Apache-2.0**):
- Qwen3 4B, GGUF Q4_K_M, from `huggingface.co/Qwen/Qwen3-4B-GGUF`
- Qwen2.5 1.5B Instruct, GGUF Q4_K_M, from `huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF`
- Qwen3 0.6B, GGUF Q4_K_M, from `huggingface.co/unsloth/Qwen3-0.6B-GGUF` (pinned revision)

If you choose another GGUF model, its own license applies (e.g. Llama Community License, Gemma Terms). Check it before use or redistribution.

## Software components

FastAPI, Starlette, Uvicorn and Pydantic (MIT/BSD); llama.cpp and llama-cpp-python (MIT); ONNX Runtime (MIT); NumPy (BSD); pypdf (BSD); platformdirs (MIT); httpx (BSD); pywebview (BSD).

**Privacy notes on dependencies**
- `opentelemetry-api` is installed as a FastAPI dependency. Without an SDK and exporter it is a no-op, and the app configures none.
- ONNX Runtime's optional Windows telemetry is switched off at start-up (`disable_telemetry_events()`).

## Fonts

**Outfit** and **Literata** are bundled under the SIL Open Font License 1.1 (`bible_narrator/web/fonts/OFL-*.txt`). They were chosen as openly licensed alternatives to the proprietary Satoshi typeface used in the design references.

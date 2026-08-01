Place `bible.sqlite` here before building the app:

    cd ../content
    python3 fetch_sources.py && python3 build.py && python3 integrity_check.py
    cp output/bible.sqlite ../app/assets/

The file is gitignored (46 MB, deterministic rebuild).

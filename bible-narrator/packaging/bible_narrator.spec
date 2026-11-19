# PyInstaller spec: builds a self-contained "Bible Narrator" folder (onedir).
#   pyinstaller packaging/bible_narrator.spec --noconfirm
# Output: dist/BibleNarrator/ (Windows: BibleNarrator.exe, macOS: dist/BibleNarrator.app)
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 (SPECPATH is provided by PyInstaller)

datas = [
    (str(ROOT / "bible_narrator" / "web"), "bible_narrator/web"),
    (str(ROOT / "bible_narrator" / "data"), "bible_narrator/data"),
]
datas += collect_data_files("espeakng_loader")   # eSpeak NG data (voices, phoneme tables)
datas += collect_data_files("kokoro_onnx")
datas += collect_data_files("phonemizer")
datas += collect_data_files("llama_cpp")
datas += collect_data_files("webview")
binaries = collect_dynamic_libs("espeakng_loader") + collect_dynamic_libs("llama_cpp") + collect_dynamic_libs("onnxruntime")
hiddenimports = (collect_submodules("uvicorn") + collect_submodules("webview") + collect_submodules("phonemizer")
                 + ["bible_narrator.server"])

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "pytest", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="BibleNarrator",
    console=False,
    icon=str(ROOT / "packaging" / "icon.ico") if sys.platform == "win32" and (ROOT / "packaging" / "icon.ico").exists() else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="BibleNarrator")  # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="BibleNarrator.app",
        icon=str(ROOT / "packaging" / "icon.icns") if (ROOT / "packaging" / "icon.icns").exists() else None,
        bundle_identifier="org.biblenarrator.app",
        info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": "1.0.0"},
    )

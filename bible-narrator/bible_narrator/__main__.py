"""Start Bible Narrator.

    python -m bible_narrator              # desktop window (pywebview)
    python -m bible_narrator --browser    # use your default web browser instead
    python -m bible_narrator --server --port 8765 --token devtoken   # headless (tests)
"""
from __future__ import annotations

import argparse
import logging
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser

from .config import APP_DISPLAY_NAME


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DesktopApi:
    """Functions the web UI can call through pywebview (native file dialogs)."""

    def __init__(self):
        self.window = None

    def choose_file(self, kind: str = "any"):
        import webview

        types = {
            "gguf": ("Language model (*.gguf)",),
            "folder": None,
        }.get(kind, ("All files (*.*)",))
        if kind == "folder":
            result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        else:
            result = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=types)
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bible-narrator", description=APP_DISPLAY_NAME)
    ap.add_argument("--data-dir", help="Folder for the library, settings, models and cache")
    ap.add_argument("--browser", action="store_true", help="Open in the default web browser instead of a desktop window")
    ap.add_argument("--server", action="store_true", help="Run the local server only (no window)")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--token", help="Fixed API token (default: random per launch)")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    import uvicorn

    from .server import AppState, create_app

    state = AppState(args.data_dir)
    token = args.token or secrets.token_urlsafe(24)
    app = create_app(state, token=token)
    port = args.port or _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    url = f"http://127.0.0.1:{port}/#token={token}"

    if args.server:
        print(f"{APP_DISPLAY_NAME} listening on {url}", flush=True)
        server.run()
        return 0

    thread = threading.Thread(target=server.run, daemon=True, name="uvicorn")
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)

    if not args.browser:
        try:
            import webview

            api = DesktopApi()
            window = webview.create_window(APP_DISPLAY_NAME, url, js_api=api, width=1280, height=860, min_size=(900, 640),
                                           background_color="#f2f0ea")
            api.window = window
            webview.start(private_mode=False, storage_path=str(state.paths.data / "webview"))
            server.should_exit = True
            return 0
        except Exception as e:  # noqa: BLE001 - no GUI toolkit available: fall back to the browser
            logging.warning("Desktop window unavailable (%s); opening in your web browser instead.", e)
    print(f"{APP_DISPLAY_NAME} is running at {url}\nClose this window or press Ctrl+C to quit.", flush=True)
    webbrowser.open(url)
    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.should_exit = True
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.exit(main())

"""Local language-model backends.

* ``LlamaCppBackend``  - runs a GGUF open-weight model in-process with llama.cpp.
* ``LocalServerBackend`` - talks to an OpenAI-compatible server that the user
  already runs on this computer (Ollama, LM Studio, llama.cpp server). Only
  loopback addresses are accepted, so text never leaves the machine.

Both return JSON constrained by a schema, which keeps small models on task and
makes their output machine-checkable.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    pass


def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def parse_json_lenient(text: str) -> dict[str, Any]:
    text = _strip_thinking(text)
    try:
        return json.loads(text)
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except ValueError:
            pass
    if start >= 0:
        repaired = repair_truncated_json(text[start:])
        if repaired is not None:
            return repaired
    raise ValueError("The model did not return valid JSON.")


def repair_truncated_json(text: str) -> dict[str, Any] | None:
    """Recover the complete part of JSON that was cut off by the token limit:
    drop the unfinished trailing element and close the open brackets."""
    for cut in range(len(text), 0, -1):
        if text[cut - 1] not in "}]\"":
            continue
        candidate = text[:cut]
        stack, in_str, esc = [], False, False
        for ch in candidate:
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack:
                stack.pop()
        if in_str:
            continue
        try:
            obj = json.loads(candidate.rstrip().rstrip(",") + "".join(reversed(stack)))
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    return None


class LlamaCppBackend:
    name = "llamacpp"

    def __init__(self, model_path: str, n_ctx: int = 8192, n_threads: int = 0):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads or max(1, (os.cpu_count() or 4) - 1)
        self._llm = None
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()
        self.state = "idle"
        self.error = ""
        self.metadata: dict[str, Any] = {}

    def load(self) -> None:
        with self._load_lock:
            if self._llm is not None:
                return
            if not self.model_path or not Path(self.model_path).is_file():
                self.state, self.error = "error", "Model file not found. Choose a .gguf file or download a model."
                raise LLMUnavailable(self.error)
            self.state, self.error = "loading", ""
            try:
                from llama_cpp import Llama
            except ImportError as e:  # pragma: no cover
                self.state, self.error = "error", "llama-cpp-python is not installed."
                raise LLMUnavailable(self.error) from e
            try:
                t = time.time()
                self._llm = Llama(model_path=self.model_path, n_ctx=self.n_ctx, n_threads=self.n_threads, verbose=False)
                self.metadata = dict(self._llm.metadata or {})
                log.info("Loaded %s in %.1fs", self.model_path, time.time() - t)
                self.state = "ready"
            except Exception as e:  # noqa: BLE001
                self.state, self.error = "error", f"Could not load the model: {e}"
                raise LLMUnavailable(self.error) from e

    def load_async(self) -> None:
        def run():
            try:
                self.load()
            except LLMUnavailable:
                pass

        threading.Thread(target=run, daemon=True, name="llm-load").start()

    def info(self) -> dict[str, Any]:
        name = self.metadata.get("general.name") or Path(self.model_path).stem if self.model_path else ""
        return {
            "backend": self.name,
            "state": self.state,
            "error": self.error,
            "model": name,
            "path": self.model_path,
            "license": self.metadata.get("general.license", ""),
            "size_bytes": Path(self.model_path).stat().st_size if self.model_path and Path(self.model_path).is_file() else 0,
            "context": self.n_ctx,
        }

    def chat_json(self, messages: list[dict[str, str]], schema: dict[str, Any], max_tokens: int = 600,
                  temperature: float = 0.1) -> dict[str, Any]:
        self.load()
        assert self._llm is not None
        with self._lock:
            r = self._llm.create_chat_completion(
                messages=messages,
                response_format={"type": "json_object", "schema": schema},
                temperature=temperature,
                top_p=0.9,
                repeat_penalty=1.05,
                max_tokens=max_tokens,
            )
        return parse_json_lenient(r["choices"][0]["message"]["content"] or "")


def is_loopback_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class LocalServerBackend:
    name = "local_server"

    def __init__(self, base_url: str, model: str = ""):
        if not is_loopback_url(base_url):
            raise LLMUnavailable("For privacy, only a server on this computer (localhost / 127.0.0.1) can be used.")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.state = "idle"
        self.error = ""

    def _client(self):
        import httpx

        # trust_env=False: never route local traffic through a system proxy.
        return httpx.Client(timeout=httpx.Timeout(300.0, connect=5.0), trust_env=False)

    def load(self) -> None:
        try:
            with self._client() as c:
                r = c.get(f"{self.base_url}/models")
                r.raise_for_status()
                models = [m.get("id") for m in r.json().get("data", [])]
                if not self.model and models:
                    self.model = models[0]
            self.state, self.error = "ready", ""
        except Exception as e:  # noqa: BLE001
            self.state, self.error = "error", f"Could not reach the local model server at {self.base_url}: {e}"
            raise LLMUnavailable(self.error) from e

    def load_async(self) -> None:
        threading.Thread(target=lambda: self._safe_load(), daemon=True).start()

    def _safe_load(self) -> None:
        try:
            self.load()
        except LLMUnavailable:
            pass

    def info(self) -> dict[str, Any]:
        return {"backend": self.name, "state": self.state, "error": self.error, "model": self.model,
                "path": self.base_url, "license": "", "size_bytes": 0, "context": 0}

    def chat_json(self, messages: list[dict[str, str]], schema: dict[str, Any], max_tokens: int = 600,
                  temperature: float = 0.1) -> dict[str, Any]:
        if self.state != "ready":
            self.load()
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_schema", "json_schema": {"name": "response", "schema": schema, "strict": True}},
        }
        with self._client() as c:
            r = c.post(f"{self.base_url}/chat/completions", json=body)
            if r.status_code == 400:  # server without json_schema support
                body["response_format"] = {"type": "json_object"}
                r = c.post(f"{self.base_url}/chat/completions", json=body)
            r.raise_for_status()
            return parse_json_lenient(r.json()["choices"][0]["message"]["content"] or "")


class LLMManager:
    """Owns the active backend and rebuilds it when settings change."""

    def __init__(self, settings):
        self.settings = settings
        self.backend: LlamaCppBackend | LocalServerBackend | None = None
        self._config: tuple | None = None
        self.configure()

    def configure(self, load: bool = True) -> None:
        s = self.settings
        cfg = (s.get("llm_backend"), s.get("model_path"), s.get("local_server_url"), s.get("local_server_model"),
               s.get("n_ctx"), s.get("n_threads"))
        if cfg == self._config:
            return
        self._config = cfg
        backend = s.get("llm_backend")
        self.backend = None
        try:
            if backend == "llamacpp" and s.get("model_path"):
                self.backend = LlamaCppBackend(s.get("model_path"), int(s.get("n_ctx") or 8192), int(s.get("n_threads") or 0))
            elif backend == "local_server" and s.get("local_server_url"):
                self.backend = LocalServerBackend(s.get("local_server_url"), s.get("local_server_model") or "")
        except LLMUnavailable as e:
            self._error = str(e)
        if self.backend and load:
            self.backend.load_async()

    @property
    def available(self) -> bool:
        return self.backend is not None and self.backend.state in ("ready", "loading", "idle")

    def status(self) -> dict[str, Any]:
        if self.backend is None:
            return {"backend": self.settings.get("llm_backend"), "state": "not_configured", "error": getattr(self, "_error", ""),
                    "model": "", "path": "", "license": "", "size_bytes": 0, "context": 0}
        return self.backend.info()

    def chat_json(self, *args, **kwargs) -> dict[str, Any]:
        if self.backend is None:
            raise LLMUnavailable("No language model is set up. Open Settings → Language model to add one.")
        return self.backend.chat_json(*args, **kwargs)

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bible_narrator.server import AppState, create_app  # noqa: E402


class FakeBackend:
    """Stands in for the local model so validation logic can be tested deterministically.

    `answer`, `retell` and `verify` hold what the "model" returns for each kind of call;
    every call is recorded in `calls`."""

    name = "fake"

    def __init__(self):
        self.state = "ready"
        self.answer = {"status": "not_in_sources", "answer": ""}
        self.retell = {"sentences": []}
        self.verify = "yes"
        self.references: list[str] = []
        self.calls: list[str] = []

    def info(self):
        return {"backend": "fake", "state": "ready", "error": "", "model": "fake-model", "path": "", "license": "",
                "size_bytes": 0, "context": 0}

    def load_async(self):
        pass

    def chat_json(self, messages, schema, max_tokens=600, temperature=0.1):
        props = schema.get("properties", {})
        if "keywords" in props:
            self.calls.append("keywords")
            return {"keywords": []}
        if "supported" in props:
            self.calls.append("verify")
            return {"supported": self.verify(messages) if callable(self.verify) else self.verify}
        if "references" in props:
            self.calls.append("references")
            return {"references": self.references}
        if "sentences" in props:
            self.calls.append("retell")
            return self.retell
        self.calls.append("answer")
        return self.answer


@pytest.fixture(scope="session")
def state(tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    os.environ.pop("BIBLE_NARRATOR_DATA", None)
    return AppState(str(data))


@pytest.fixture()
def fake_llm(state):
    fake = FakeBackend()
    previous = state.llm.backend
    state.llm.backend = fake
    yield fake
    state.llm.backend = previous


@pytest.fixture(scope="session")
def client(state):
    from fastapi.testclient import TestClient

    app = create_app(state, token="test-token")
    c = TestClient(app)
    c.headers.update({"X-App-Token": "test-token"})
    return c

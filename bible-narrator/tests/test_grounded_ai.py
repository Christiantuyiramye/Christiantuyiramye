"""Honesty rules for Ask and Retell, tested with a scripted stand-in for the model."""
from bible_narrator.answer import NOT_FOUND
from bible_narrator.grounding import is_moralizing, support_ratio, unsupported_names, unsupported_quotes


def test_grounding_primitives():
    src = "Abraham rose early in the morning and saddled his donkey."
    assert support_ratio("Abraham saddled his donkey early.", src) == 1.0
    assert support_ratio("Abraham rode a camel to Egypt.", src) < 0.5
    assert unsupported_names("Early on, Abraham and Sarah left.", src) == ["Sarah"]
    assert unsupported_quotes('He said "let us go".', src) == ["let us go"]
    assert unsupported_quotes('He "saddled his donkey".', src) == []
    assert is_moralizing("This story teaches us to trust.")
    assert not is_moralizing("Abraham trusted God.")


# ---------------------------------------------------------------- Ask

def test_unrelated_question_is_not_found_without_calling_the_model(state, fake_llm):
    r = state.answers.ask("What is the capital of Australia?")
    assert r["status"] == "not_found"
    assert r["answer"] == NOT_FOUND
    assert "answer" not in fake_llm.calls  # gated before generation


def test_model_reporting_no_answer_gives_plain_not_found(state, fake_llm):
    fake_llm.answer = {"status": "not_in_sources", "answer": ""}
    r = state.answers.ask("What was the name of Noah's wife?")
    assert r["status"] == "not_found" and r["answer"] == NOT_FOUND


def test_invented_fact_is_withheld(state, fake_llm):
    # Scripture never names Noah's wife; a model inventing a name must not get through.
    fake_llm.answer = {"status": "answered", "answer": "Noah's wife was named Naamah [1]."}
    r = state.answers.ask("What was the name of Noah's wife?")
    assert r["status"] == "not_found"
    assert r["answer"] == NOT_FOUND
    assert r["removed"] and "Naamah" in r["removed"][0]["text"]


def test_supported_answer_keeps_citations_and_labels_sources(state, fake_llm):
    fake_llm.answer = {"status": "answered", "answer": "In the beginning God created the heavens and the earth [1]."}
    r = state.answers.ask("What did God create in the beginning according to Genesis 1:1?")
    assert r["status"] == "answered"
    assert r["citations"][0]["is_scripture"] and r["citations"][0]["label"].startswith("Genesis 1:1")
    assert r["segments"][0]["cites"] == [1]
    assert "[1]" in r["answer"]


def test_wrong_citation_number_is_corrected_or_dropped(state, fake_llm):
    fake_llm.answer = {"status": "answered", "answer": "In the beginning God created the heavens and the earth [9]."}
    r = state.answers.ask("What did God create in the beginning according to Genesis 1:1?")
    assert r["status"] == "answered"  # re-cited to the source that actually supports it
    assert r["citations"][0]["label"].startswith("Genesis 1:1")


def test_fabricated_quote_is_removed(state, fake_llm):
    fake_llm.answer = {"status": "answered",
                       "answer": 'God created the heavens and the earth [1]. God said "I made all this for joy" [1].'}
    r = state.answers.ask("What did God create in the beginning according to Genesis 1:1?")
    assert len(r["segments"]) == 1
    assert any("joy" in x["text"] for x in r["removed"])


def test_verification_check_can_withhold(state, fake_llm):
    fake_llm.answer = {"status": "answered", "answer": "In the beginning God created the heavens and the earth [1]."}
    fake_llm.verify = "no"
    r = state.answers.ask("What did God create in the beginning according to Genesis 1:1?")
    assert r["status"] == "not_found" and r["answer"] == NOT_FOUND


def test_commentary_only_answers_are_flagged(state, fake_llm):
    fake_llm.answer = {"status": "answered",
                       "answer": "Easton's Bible Dictionary says Melchizedek was king of Salem and priest of the most high God [1]."}
    r = state.answers.ask("Who was Melchizedek?")
    if r["status"] == "answered" and not any(c["is_scripture"] for c in r["citations"]):
        assert any("not directly from Scripture" in n for n in r["notes"])
    assert all(c["kind"] in ("scripture", "dictionary", "commentary", "reference") for c in r["citations"])


def test_no_model_returns_search_results_not_an_answer(state):
    previous = state.llm.backend
    state.llm.backend = None
    try:
        r = state.answers.ask("Who was Melchizedek?")
    finally:
        state.llm.backend = previous
    assert r["status"] == "no_model" and r["answer"] == "" and r["related"]


# ---------------------------------------------------------------- Retell

def bsb_id(state):
    return state.library.default_scripture_id(state.settings.get("default_translation"))


def test_faithful_retelling_is_kept(state, fake_llm):
    fake_llm.retell = {"sentences": [
        {"text": "That evening Jesus told His disciples to cross to the other side.", "refs": ["4:35"]},
        {"text": "A great windstorm arose and the waves broke over the boat.", "refs": ["4:37"]},
        {"text": "Jesus rebuked the wind and the sea, and it was perfectly calm.", "refs": ["4:39"]},
    ]}
    r = state.retell.retell("Mark 4:35-41", bsb_id(state))
    assert r["mode"] == "retelling"
    assert [s["refs"][0] for s in r["sentences"]] == ["Mark 4:35", "Mark 4:37", "Mark 4:39"]
    assert r["removed"] == []


def test_retelling_additions_are_removed(state, fake_llm):
    fake_llm.retell = {"sentences": [
        {"text": "That evening Jesus told His disciples to cross to the other side.", "refs": ["4:35"]},
        {"text": "Peter, terrified, gripped the mast as thunder roared.", "refs": ["4:37"]},  # invented name/details
        {"text": "Jesus rebuked the wind and the sea, and it was perfectly calm.", "refs": ["4:39"]},
        {"text": "This story teaches us to trust God in our own storms.", "refs": ["4:40"]},  # moral
        {"text": "A great windstorm arose and the waves broke over the boat.", "refs": ["4:37"]},
    ]}
    r = state.retell.retell("Mark 4:35-41", bsb_id(state))
    assert r["mode"] == "retelling"
    texts = " ".join(s["text"] for s in r["sentences"])
    assert "Peter" not in texts and "teaches" not in texts
    reasons = " ".join(x["reason"] for x in r["removed"])
    assert "names not in the passage" in reasons and "lesson" in reasons


def test_untrustworthy_retelling_falls_back_to_exact_verses(state, fake_llm):
    fake_llm.retell = {"sentences": [
        {"text": "Jesus and Peter sailed to Rome to meet Caesar.", "refs": ["4:35"]},
        {"text": "This shows us that faith is a lesson for our lives.", "refs": ["4:40"]},
    ]}
    r = state.retell.retell("Mark 4:35-41", bsb_id(state))
    assert r["mode"] == "condensed"
    assert all(s.get("verbatim") for s in r["sentences"])
    verses = {f"{v['chapter']}:{v['verse']}": v["text"] for v in r["verses"]}
    assert all(s["text"] == verses[s["verse_keys"][0]] for s in r["sentences"])  # exact text only


def test_retell_without_model_is_condensed_and_labeled(state):
    previous = state.llm.backend
    state.llm.backend = None
    try:
        r = state.retell.retell("Genesis 22:1-14", bsb_id(state))
    finally:
        state.llm.backend = previous
    assert r["mode"] == "condensed" and "needs a local language model" in r["notes"][0]

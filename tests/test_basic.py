import pytest

from src import ai_engine, demo_data, evaluation, safety, verification, vision
from src.agent import Agent
from src.ai_engine import DemoProvider
from src.memory import SessionMemory


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(safety, "DEMO_WORKSPACE", tmp_path / "ws")
    safety.reset_workspace()


def make_agent(fail_first=False, scenario="debug"):
    return Agent(DemoProvider(scenario, fail_first), pace=0)


def test_parse_json_and_fallback():
    assert ai_engine.parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}
    assert ai_engine.parse_json_response("not json") is None
    fb = ai_engine.fallback_analysis("plain text")
    assert fb["fallback"] and not fb["requires_approval"]


def test_normalize_fills_defaults():
    n = ai_engine.normalize_analysis({"action_plan": "one step"})
    assert n["action_plan"] == ["one step"] and n["confidence"].startswith("Low")


def test_safety_blocks_bad_actions(tmp_path):
    assert not safety.validate_action(safety.ActionRequest("run_shell", "x", "r"))[0]
    assert not safety.validate_action(safety.ActionRequest("patch_demo_file", "../../etc/passwd", "r"))[0]
    assert not safety.validate_action(safety.ActionRequest("patch_demo_file", "app.py", "r", replace="os.system('x')"))[0]
    assert safety.scan_risky("run sudo rm -rf /")


def test_patch_requires_unique_match():
    ok, _ = safety.apply_demo_patch(safety.ActionRequest("patch_demo_file", "app.py", "r", find="nonexistent", replace="x"))
    assert not ok


def test_verification_fails_then_succeeds():
    assert verification.verify_demo_workspace()["status"] == "failed"  # NameError
    a = demo_data.get_analysis("debug", 0, False, "Beginner")["action"]
    safety.apply_demo_patch(safety.ActionRequest(**a))
    assert verification.verify_demo_workspace()["status"] == "success"


def test_full_closed_loop_happy_path():
    ag = make_agent()
    assert ag.submit("I need to get this program running.", b"img")
    assert ag.state == "WAITING_FOR_APPROVAL" and ag.memory.goal
    ag.approve()
    assert ag.state == "RESOLVED" and ag.verification["status"] == "success"
    labels = [e.label for e in ag.memory.timeline]
    assert "Waiting for approval" in labels and "Verification complete" in labels


def test_reanalysis_loop_when_first_fix_incomplete():
    ag = make_agent(fail_first=True)
    ag.submit("fix it", None)
    ag.approve()
    assert ag.state == "WAITING_FOR_APPROVAL" and ag.attempt == 1 and ag.memory.attempts
    assert "still" in ag.memory.attempts[0]["outcome"].lower() or "output" in ag.memory.attempts[0]["outcome"].lower()
    ag.approve()
    assert ag.state == "RESOLVED"


def test_reject_changes_nothing():
    ag = make_agent()
    ag.submit("fix it", None)
    ag.reject()
    assert ag.state == "READY" and "remainder = num" not in safety.read_workspace_file()


def test_empty_request_is_a_friendly_error():
    ag = make_agent()
    assert not ag.submit("  ", None) and ag.state == "ERROR"


def test_explanation_only_scenario_resolves_without_approval():
    ag = make_agent(scenario="chart")
    ag.submit("Explain what I'm looking at.", b"x")
    assert ag.state == "RESOLVED"


def test_session_memory_context_and_followup():
    ag = make_agent()
    ag.submit("fix it", None)
    ag.submit("Okay, I did that. What next?", None)
    assert ag.state == "WAITING_FOR_APPROVAL"
    assert "Issue:" in ag.memory.context_text()
    ag.memory.reset()
    assert "no history" in ag.memory.context_text()


def test_vision_validation_and_highlight():
    with pytest.raises(ValueError):
        vision.load_image(b"not an image", "x.png")
    with pytest.raises(ValueError):
        vision.load_image(b"abc", "x.exe")
    demo_data.ensure_demo_assets()
    png = vision.load_image(demo_data.IMAGES["debug"].read_bytes(), "s.png")
    assert vision.annotate(png, [0.1, 0.1, 0.2, 0.2])[1]
    assert not vision.annotate(png, None)[1] and not vision.annotate(png, [2, 2, 5, 5])[1]


def test_gemini_requires_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ai_engine.AIError):
        ai_engine.GeminiProvider()


def test_error_classification():
    assert "key" in ai_engine.classify_error(Exception("403 permission denied")).user_message.lower()
    assert "long" in ai_engine.classify_error(Exception("Request timed out")).user_message.lower()


def test_evaluation_summary_and_csv():
    assert evaluation.summarize([]) is None
    r = [{"case": 1, "scenario": "a", "time_to_resolution_s": 60, "issue_identified_correctly": True,
          "recommendation_useful": True, "verification_succeeded": False, "notes": ""}]
    assert evaluation.summarize(r)["avg_time_s"] == 60 and "scenario" in evaluation.to_csv(r)


def test_app_demo_flow_end_to_end():
    pytest.importorskip("streamlit.testing.v1")
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=90).run()
    assert not at.exception, at.exception
    btn = lambda label: next(b for b in at.button if b.label == label)
    btn("Capture context").click().run()
    btn("Use sample request").click().run()
    btn("Analyze and guide").click().run()
    assert not at.exception, at.exception
    assert any(b.label == "Approve" for b in at.button)
    btn("Approve").click().run()
    assert not at.exception, at.exception
    assert any("ISSUE RESOLVED" in m.value for m in at.markdown)

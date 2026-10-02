"""ContextBridge: real-time AI that hears you and sees your screen. Team Novyra · AI Build Challenge 2026 · PS-05."""
from __future__ import annotations

import hashlib
import html
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="ContextBridge · Novyra", page_icon="🌉", layout="wide")
load_dotenv()

from src import demo_data, evaluation, safety, speech, vision  # noqa: E402
from src.agent import STATE_META, Agent  # noqa: E402
from src.ai_engine import LEVELS, AIError, DemoProvider, GeminiProvider  # noqa: E402

esc = html.escape
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', system-ui, sans-serif; }
.stApp { background: radial-gradient(1200px 500px at 15% -10%, #12263a 0%, transparent 60%), #0a0e14; }
#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; }
.block-container { padding-top: 1.6rem; max-width: 1500px; }
.cb-title { font-size: 2rem; font-weight: 600; letter-spacing: -0.02em; margin: 0; color: #f1f5f9; }
.cb-title span { background: linear-gradient(90deg,#5eead4,#818cf8); -webkit-background-clip: text; color: transparent; }
.cb-sub { color: #94a3b8; margin: .15rem 0 0; font-size: .98rem; }
.cb-tag { color: #5eead4; font-size: .9rem; margin: .1rem 0 .9rem; }
.cb-pills { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: .9rem; }
.cb-pill { display: inline-flex; align-items: center; gap: .45rem; padding: .28rem .7rem; border-radius: 999px;
  background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08); color: #cbd5e1; font-size: .8rem; }
.cb-pill i { width: .5rem; height: .5rem; border-radius: 50%; background: #64748b; }
.cb-pill b { font-weight: 500; color: #94a3b8; }
.cb-pill.ok i { background: #34d399; box-shadow: 0 0 8px #34d39988; } .cb-pill.warn i { background: #fbbf24; }
.cb-pill.err i { background: #f87171; } 
.cb-banner { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
  padding: .9rem 1.2rem; border-radius: 14px; margin-bottom: 1rem; border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
  background: linear-gradient(90deg, color-mix(in srgb, var(--c) 14%, #0f1520), #0f1520 70%); }
.cb-bl { display: flex; align-items: center; gap: .9rem; }
.cb-dot { width: .85rem; height: .85rem; border-radius: 50%; background: var(--c); box-shadow: 0 0 14px var(--c); }
.cb-state { font-weight: 600; letter-spacing: .08em; color: var(--c); font-size: 1.05rem; }
.cb-desc { color: #94a3b8; font-size: .86rem; }
.cb-steps { display: flex; gap: .35rem; flex-wrap: wrap; }
.cb-step { padding: .2rem .65rem; border-radius: 6px; font-size: .75rem; color: #64748b; border: 1px solid rgba(255,255,255,.07); }
.cb-step.done { color: #34d399; border-color: #34d39955; } .cb-step.now { color: #0a0e14; background: var(--c); border-color: var(--c); font-weight: 600; }
.cb-label { color: #8aa0b8; font-size: .78rem; font-weight: 500; letter-spacing: .04em; margin-bottom: .35rem; }
.cb-row { padding: .65rem 0; border-top: 1px solid rgba(255,255,255,.06); }
.cb-row:first-of-type { border-top: 0; }
.cb-val { color: #e6edf3; font-size: .98rem; line-height: 1.5; }
.cb-fix { font-family: 'IBM Plex Mono', monospace; font-size: .88rem; background: #0d1520; border: 1px solid #1f3347;
  border-left: 3px solid #5eead4; padding: .65rem .8rem; border-radius: 8px; color: #d6f5ef; }
.cb-badge { display: inline-block; padding: .15rem .6rem; border-radius: 6px; font-size: .78rem; font-weight: 500; }
.cb-badge.demo { background: #fbbf2422; color: #fbbf24; border: 1px solid #fbbf2455; }
.cb-conf-High { background: #34d39922; color: #34d399; } .cb-conf-Medium { background: #fbbf2422; color: #fbbf24; }
.cb-conf-Low { background: #f8717122; color: #f87171; }
.cb-plan { margin: .2rem 0 0; padding-left: 1.2rem; color: #e6edf3; } .cb-plan li { margin: .25rem 0; }
.cb-ok { border: 1px solid #34d39966; background: #34d3991a; border-radius: 12px; padding: .9rem 1.1rem; color: #a7f3d0; }
.cb-bad { border: 1px solid #fbbf2466; background: #fbbf241a; border-radius: 12px; padding: .8rem 1rem; color: #fde68a; margin-bottom: .6rem; }
.cb-appr { border: 1px solid #fbbf2477; background: #fbbf2410; border-radius: 12px; padding: .8rem 1rem; margin-bottom: .6rem; color: #fde68a; font-weight: 600; letter-spacing: .04em; }
.cb-tl { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: .6rem; }
.cb-ev { padding: .55rem .75rem; border-radius: 10px; background: rgba(255,255,255,.035); border: 1px solid rgba(255,255,255,.06);
  border-left: 3px solid #475569; } .cb-ev.ok { border-left-color: #34d399; } .cb-ev.warn { border-left-color: #fbbf24; } .cb-ev.err { border-left-color: #f87171; }
.cb-ev small { color: #64748b; font-family: 'IBM Plex Mono', monospace; } .cb-ev div { color: #e2e8f0; font-size: .88rem; }
.cb-ev span { color: #8aa0b8; font-size: .78rem; }
.stButton > button { width: 100%; border-radius: 10px; font-weight: 500; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; background: rgba(255,255,255,.025); }
@media (max-width: 900px) { .cb-title { font-size: 1.5rem; } }
</style>
"""
LOOP = ["Understand", "Diagnose", "Plan", "Approve", "Act", "Verify"]
STEP_IDX = {"LISTENING": 0, "ANALYZING": 1, "RE_ANALYZING": 1, "PLANNING": 2, "WAITING_FOR_APPROVAL": 3,
            "ACTING": 4, "VERIFYING": 5, "RESOLVED": 6}


# ------------------------------------------------------------------ view helpers
def pill(label: str, tone: str, text: str) -> str:
    return f'<span class="cb-pill {tone}"><i></i>{esc(label)}<b>{esc(text)}</b></span>'


def banner_html(agent: Agent) -> str:
    label, color, desc = STATE_META[agent.state]
    idx = STEP_IDX.get(agent.state, -1)
    steps = "".join(f'<span class="cb-step {"done" if idx > i else "now" if idx == i else ""}">{n}</span>' for i, n in enumerate(LOOP))
    return (f'<div class="cb-banner" style="--c:{color}"><div class="cb-bl"><span class="cb-dot"></span><div>'
            f'<div class="cb-state">{label}</div><div class="cb-desc">{esc(agent.state_detail or desc)}</div></div></div>'
            f'<div class="cb-steps">{steps}</div></div>')


def label(text: str) -> None:
    st.markdown(f'<div class="cb-label">{esc(text)}</div>', unsafe_allow_html=True)


def analysis_html(a: dict) -> str:
    conf = a["confidence"]
    tone = next((t for t in ("High", "Medium", "Low") if conf.startswith(t)), "Low")
    def row(t, v):
        return f'<div class="cb-row"><div class="cb-label">{t}</div><div class="cb-val">{v}</div></div>'
    parts = [row("Goal", esc(a["goal"])), row("Problem detected", esc(a["issue"])), row("Location", esc(a["location"])),
             row("Why it happens", esc(a["explanation"] or a["cause"])),
             row("Suggested fix", f'<div class="cb-fix">{esc(a["suggested_fix"])}</div>'),
             row("Confidence", f'<span class="cb-badge cb-conf-{tone}">{esc(conf)}</span>')]
    if a["action_plan"]:
        items = "".join(f"<li>{esc(s)}</li>" for s in a["action_plan"])
        parts.append(row("Action plan", f'<ol class="cb-plan">{items}</ol>'))
    if a["verification_plan"]:
        parts.append(row("How we will verify", esc(a["verification_plan"])))
    return "".join(parts)


def timeline_html(events) -> str:
    if not events:
        return '<div class="cb-desc">No events yet. The agent timeline fills in as ContextBridge works.</div>'
    return '<div class="cb-tl">' + "".join(
        f'<div class="cb-ev {e.kind}"><small>{e.ts}</small><div>{esc(e.label)}</div><span>{esc(e.detail[:110])}</span></div>'
        for e in events) + "</div>"


def speak(text: str) -> None:
    if st.session_state.get("speak") and text:
        audio, err = speech.synthesize(text)
        if audio:
            st.session_state.tts = audio
        elif err:
            st.session_state.tts_err = err


# ------------------------------------------------------------------ state
ss = st.session_state
for k, v in {"agent": Agent(), "ctx": None, "up_n": 0, "cam_n": 0, "audio_hash": None, "eval": [], "request_text": "",
             "mode": "Live AI (Gemini)" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "Demo Mode",
             "tts": None, "tts_err": None, "speak": False}.items():
    ss.setdefault(k, v)
agent: Agent = ss.agent
demo_data.ensure_demo_assets()
if not safety.DEMO_WORKSPACE.joinpath("app.py").exists():
    safety.reset_workspace()
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### Session setup")
    st.radio("Mode", ["Demo Mode", "Live AI (Gemini)"], key="mode",
             help="Demo Mode is scripted and works offline. Live AI sends your input to Gemini.")
    is_demo = ss.mode == "Demo Mode"
    scenario, fail_first = "debug", False
    if is_demo:
        scenario = st.selectbox("Demo scenario", list(demo_data.SCENARIOS), format_func=lambda k: demo_data.SCENARIOS[k]["title"])
        if scenario == "debug":
            fail_first = st.toggle("Simulate an incomplete first fix", value=False,
                                   help="Shows the verify → fail → re-analyze loop. The failure is detected by really running the sandbox file.")
        st.caption("Demo Mode is scripted. It does **not** call an AI model.")
    st.toggle("Speak responses (TTS)", key="speak", help="Uses gTTS and needs internet. Text is always shown.")
    cfg = (ss.mode, scenario, fail_first)
    if ss.get("cfg") != cfg:
        ss.cfg = cfg
        agent.reset()
        ss.ctx, ss.request_text = None, ""
        safety.reset_workspace()
    if st.button("Clear session"):
        agent.reset()
        ss.ctx, ss.request_text, ss.up_n, ss.cam_n = None, "", ss.up_n + 1, ss.cam_n + 1
        safety.reset_workspace()
        st.rerun()
    st.divider()
    st.caption("Safety: no shell commands, no arbitrary file access. The only file action is a patch inside `demo_workspace/`, and only after approval.")

# provider
provider, provider_err = None, None
if is_demo:
    provider = DemoProvider(scenario, fail_first)
else:
    try:
        if "gemini" not in ss:
            ss.gemini = GeminiProvider()
        provider = ss.gemini
    except AIError as e:
        provider_err = e.user_message
agent.provider = provider

# ------------------------------------------------------------------ header + status
st.markdown('<h1 class="cb-title">Context<span>Bridge</span></h1>'
            '<p class="cb-sub">Real-time AI that hears you and sees your screen.</p>'
            '<p class="cb-tag">Understand. Diagnose. Guide. Verify.</p>', unsafe_allow_html=True)
has_audio = hasattr(st, "audio_input")
voice = ("neutral", "sample / typed") if is_demo else (("err", "needs API key") if provider is None else (("ok", "Gemini STT") if has_audio else ("warn", "typed only")))
ai = ("warn", "Demo Mode") if is_demo else (("ok", provider.name) if provider else ("err", "not configured"))
st.markdown('<div class="cb-pills">' + pill("Session", "err" if agent.state == "ERROR" else "ok", "Ready" if agent.state == "READY" else "Active")
            + pill("Voice", *voice) + pill("Vision", "ok" if ss.ctx else "neutral", "context captured" if ss.ctx else "no image yet")
            + pill("AI", *ai) + pill("Safety", "ok", "sandboxed") + "</div>", unsafe_allow_html=True)
if is_demo:
    st.markdown('<span class="cb-badge demo">DEMO MODE · scripted walkthrough · not a live AI result</span>', unsafe_allow_html=True)
if provider_err:
    st.error(provider_err + " You can switch to **Demo Mode** in the sidebar.")

banner = st.empty()
agent.notify = lambda a: banner.markdown(banner_html(a), unsafe_allow_html=True)
banner.markdown(banner_html(agent), unsafe_allow_html=True)

tab_ws, tab_eval = st.tabs(["Agent workspace", "Evaluation"])

# ------------------------------------------------------------------ workspace
with tab_ws:
    left, center, right = st.columns([1.05, 1.5, 1.05], gap="medium")
    a = agent.analysis

    # ---- LEFT: visual context
    with left, st.container(border=True):
        label("Visual context")
        t_up, t_cam, t_scr = st.tabs(["Upload", "Camera", "Screen"])
        up = cam = None
        with t_up:
            up = st.file_uploader("Screenshot or photo", type=["png", "jpg", "jpeg", "webp"], key=f"up_{ss.up_n}", label_visibility="collapsed")
        with t_cam:
            if st.toggle("Enable camera", key="cam_on"):
                cam = st.camera_input("Camera", key=f"cam_{ss.cam_n}", label_visibility="collapsed")
        with t_scr:
            st.caption("Browser screen-sharing is not required (it is unreliable across browsers). Take a screenshot "
                       "(Win+Shift+S / Cmd+Shift+4) and drop it in **Upload**.")
        cand = None
        if up is not None:
            cand = (up.getvalue(), up.name)
        elif cam is not None:
            cand = (cam.getvalue(), "camera.png")
        elif is_demo:
            p = demo_data.IMAGES[scenario]
            cand = (p.read_bytes(), p.name)
        c1, c2 = st.columns(2)
        if c1.button("Capture context", type="primary"):
            if cand is None:
                st.warning("Add an image first (upload, camera or demo sample).")
            else:
                try:
                    ss.ctx = vision.load_image(*cand)
                    agent.memory.log("Visual context captured", cand[1], "ok")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        if c2.button("Clear image"):
            ss.ctx, ss.up_n, ss.cam_n = None, ss.up_n + 1, ss.cam_n + 1
            st.rerun()
        if is_demo and up is not None:
            st.caption("Demo Mode never analyses uploaded images; the scripted result applies to the sample screenshot.")
        drawn = False
        try:
            if ss.ctx:
                shown, drawn = vision.annotate(ss.ctx, a.get("highlight") if a else None)
                st.image(shown, caption="Look at the highlighted area." if drawn else "Captured context.")
                if a and not drawn and not a.get("fallback"):
                    st.caption("No reliable problem region was identified, so no highlight is drawn.")
            elif cand:
                st.image(cand[0], caption="Preview. Not captured yet.")
            else:
                st.caption("No image yet. Upload a screenshot, then press **Capture context**.")
        except Exception:
            st.warning("That image can't be previewed. Try another file.")
        if not is_demo and a and a.get("highlight") and drawn:
            st.caption("Highlight is the model's estimate; it may be imprecise.")

    # ---- RIGHT: voice + goal
    with right, st.container(border=True):
        label("Voice + goal")
        if is_demo:
            if st.button("Use sample request"):
                ss.request_text = demo_data.SCENARIOS[scenario]["utterance"]
            st.caption("Demo Mode can't transcribe audio. Use the sample request or type.")
        elif has_audio and provider is not None:
            clip = st.audio_input("Speak your request")
            if clip is not None:
                data = clip.getvalue()
                h = hashlib.md5(data).hexdigest()
                if h != ss.audio_hash:
                    ss.audio_hash = h
                    agent._set("LISTENING", "Transcribing your voice")
                    try:
                        with st.spinner("Transcribing…"):
                            text = provider.transcribe(data, "audio/wav")
                        if text:
                            ss.request_text = text
                            agent.memory.log("Voice transcribed", text[:90], "ok")
                            ss.voice_src = True
                        else:
                            st.warning("I couldn't hear any speech. Try again or type below.")
                    except AIError as e:
                        st.error(e.user_message + " You can type your request instead.")
                    except Exception:
                        st.error("Voice transcription failed. You can type your request instead.")
                    agent._set("READY" if agent.state == "LISTENING" else agent.state)
        elif not is_demo:
            st.info("Microphone input needs Streamlit ≥ 1.40 and an API key. You can still type.")
        st.text_area("Transcript / request", key="request_text", height=110,
                     placeholder='e.g. "I need to get this program running. Find what\'s wrong and guide me."  Later: "Okay, I did that. What next?"')
        st.radio("Explanation level", LEVELS, horizontal=True, key="level")
        if st.button("Analyze and guide", type="primary", disabled=provider is None):
            if not is_demo and not ss.ctx:
                st.warning("No image captured, so this will be voice-only and less certain.")
            src = "voice" if ss.pop("voice_src", False) else "text"
            with st.spinner("Working…"):
                agent.submit(ss.request_text, ss.ctx, ss.level, src)
            if agent.analysis and not agent.error:
                speak(agent.analysis["spoken_summary"] or agent.analysis["explanation"])
            st.rerun()
        goal = agent.memory.goal
        st.markdown(f'<div class="cb-row"><div class="cb-label">Detected goal</div><div class="cb-val">{esc(goal) if goal else "<span class=cb-desc>Not detected yet</span>"}</div></div>', unsafe_allow_html=True)

    # ---- CENTER: analysis + approval + verification
    with center, st.container(border=True):
        label("AI analysis")
        if agent.error:
            st.error(agent.error)
        if agent.state in ("ANALYZING", "RE_ANALYZING") and not a:
            st.caption("Analyzing…")
        if a:
            if a.get("demo"):
                st.markdown('<span class="cb-badge demo">DEMO MODE · scripted</span>', unsafe_allow_html=True)
            if a.get("fallback"):
                st.warning("The model did not return structured output, so the plain-text answer is shown.")
                st.write(a["explanation"])
            else:
                st.markdown(analysis_html(a), unsafe_allow_html=True)
        else:
            st.markdown('<div class="cb-desc">Capture context, say or type what you need, then press <b>Analyze and guide</b>. '
                        'ContextBridge will diagnose, plan, ask permission, act safely and verify the result.</div>', unsafe_allow_html=True)
        for i, at in enumerate(agent.memory.attempts, 1):
            st.markdown(f'<div class="cb-bad">⚠ ISSUE STILL PRESENT after attempt {i}: {esc(at["outcome"])}</div>', unsafe_allow_html=True)

        # approval
        if agent.state == "WAITING_FOR_APPROVAL" and agent.action:
            ac = agent.action
            st.markdown('<div class="cb-appr">ACTION REQUIRES APPROVAL</div>', unsafe_allow_html=True)
            st.markdown(f"**Action:** {'Modify demo_workspace/' + ac.target if ac.kind == 'patch_demo_file' else 'Guided step (you perform it)'}  \n**Reason:** {ac.reason}")
            if ac.proposed_change:
                st.code(ac.proposed_change, language="diff" if ac.kind == "patch_demo_file" else None)
            if agent.risk_flags:
                st.warning("The suggestion mentions a potentially risky command. ContextBridge will never run it for you; review it yourself.")
            st.caption("Would you like me to proceed? Reversible; sandbox only." if ac.kind == "patch_demo_file" else "Would you like me to proceed? I will guide you; nothing is executed automatically.")
            b1, b2 = st.columns(2)
            if b1.button("Approve", type="primary"):
                agent.approve()
                speak(f"Verification: {agent.verification['detail']}" if agent.verification else "")
                st.rerun()
            if b2.button("Reject"):
                agent.reject()
                st.rerun()

        # guided live action
        if agent.state == "ACTING" and agent.awaiting_user:
            st.info("**Guided action.** Apply the suggested change yourself, then upload a fresh screenshot of the result.")
            vf = st.file_uploader("Screenshot after the fix", type=["png", "jpg", "jpeg", "webp"], key=f"vf_{ss.up_n}_{len(agent.memory.attempts)}")
            if st.button("Verify result", type="primary"):
                try:
                    img = vision.load_image(vf.getvalue(), vf.name) if vf else None
                except ValueError as e:
                    img = None
                    st.error(str(e))
                if img or not vf:
                    with st.spinner("Verifying…"):
                        agent.verify_live(img)
                    st.rerun()

        if agent.state == "RESOLVED":
            v = agent.verification
            body = "✓ ISSUE RESOLVED<br>✓ GOAL COMPLETED" if v else "✓ EXPLANATION DELIVERED<br>✓ GOAL COMPLETED"
            note = f'<br><small>{esc(v["detail"])}</small>' if v else ""
            tag = '<br><small>Simulated in Demo Mode.</small>' if v and v.get("simulated") else ""
            st.markdown(f'<div class="cb-ok"><b>{body}</b>{note}{tag}</div>', unsafe_allow_html=True)
            t = agent.memory.elapsed_seconds()
            if t is not None:
                st.caption(f"Session time: {t // 60}m {t % 60}s (see Evaluation tab to log it).")
        if ss.tts:
            st.audio(ss.pop("tts"), format="audio/mp3", autoplay=True)
        if ss.tts_err:
            st.caption(ss.pop("tts_err"))

        if is_demo and scenario == "debug":
            with st.expander("Sandboxed demo workspace · demo_workspace/app.py"):
                st.code(safety.read_workspace_file(), language="python")

    # ---- BOTTOM: timeline + conversation
    with st.container(border=True):
        label("Agent timeline")
        st.markdown(timeline_html(agent.memory.timeline), unsafe_allow_html=True)
    with st.expander(f"Conversation history ({len(agent.memory.turns)} turns)"):
        if not agent.memory.turns:
            st.caption("Nothing yet.")
        for t in agent.memory.turns:
            with st.chat_message("user" if t.role == "user" else "assistant"):
                st.write(t.text)

# ------------------------------------------------------------------ evaluation
with tab_eval:
    st.markdown("#### Evaluation log")
    st.caption(f"Targets, not results: baseline ≈ {evaluation.BASELINE_MINUTES} min per issue, goal < {evaluation.TARGET_MINUTES} min. "
               f"Log ~{evaluation.TARGET_CASES} real scenarios below. Nothing is pre-filled.")
    elapsed = agent.memory.elapsed_seconds()
    with st.form("eval_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        scen = c1.text_input("Scenario", placeholder="e.g. NameError in Flask route")
        secs = c2.number_input("Time to resolution (seconds)", min_value=0, value=int(elapsed or 0), step=5)
        d1, d2, d3 = st.columns(3)
        ident, useful, ver = d1.checkbox("Issue identified correctly"), d2.checkbox("Recommendation useful"), d3.checkbox("Verification succeeded")
        notes = st.text_input("Notes")
        if st.form_submit_button("Add to log", type="primary"):
            ss.eval.append({"case": len(ss.eval) + 1, "scenario": scen or "(untitled)", "time_to_resolution_s": int(secs),
                            "issue_identified_correctly": ident, "recommendation_useful": useful,
                            "verification_succeeded": ver, "notes": notes})
            st.rerun()
    if ss.eval:
        st.dataframe(ss.eval, hide_index=True)
        s = evaluation.summarize(ss.eval)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cases logged", f"{s['cases']} / {evaluation.TARGET_CASES}")
        m2.metric("Avg time", f"{s['avg_time_s']}s" if s["avg_time_s"] is not None else "n/a")
        m3.metric("Identified correctly", f"{s['identified_pct']}%")
        m4.metric("Verified", f"{s['verified_pct']}%")
        st.download_button("Export CSV", evaluation.to_csv(ss.eval), "contextbridge_evaluation.csv", "text/csv")
    else:
        st.info("No cases logged yet.")

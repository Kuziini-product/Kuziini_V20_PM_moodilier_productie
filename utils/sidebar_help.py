
# utils/sidebar_help.py
from __future__ import annotations
import json
from pathlib import Path
import streamlit as st

SIDEBAR_HELP_PATH = Path(__file__).resolve().parents[1] / "PM_v20_sidebar_help.json"

@st.cache_data(show_spinner=False)
def load_sidebar_help() -> dict:
    try:
        if SIDEBAR_HELP_PATH.exists():
            return json.loads(SIDEBAR_HELP_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def detect_active_key() -> str:
    for k in ("route","page","active_page","active_tab","active_section","current_view"):
        v = st.session_state.get(k)
        if isinstance(v, str) and v:
            return v
    return "dashboard"

def render_sidebar_help(active_key: str | None = None) -> None:
    help_map = load_sidebar_help()
    active = (active_key or detect_active_key()) or "dashboard"
    with st.sidebar:
        st.markdown("### 📖 Ajutor — descriere secțiuni")
        for key, meta in help_map.items():
            title = meta.get("title",""); desc = meta.get("desc","")
            if not title: st.markdown("---"); continue
            if key == active: st.markdown(f"**➡️ {title}**"); st.caption(desc)
            else: st.markdown(f"{title}"); st.caption(desc)
        st.markdown("---")

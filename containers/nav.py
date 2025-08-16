
from __future__ import annotations
from typing import Dict, Any
import streamlit as st
from datetime import datetime
import os, base64, glob

NAV = {
    "Dashboard": "dashboard",
    "Vedere generală": "overview",
    "Secțiuni": "sections",
    "Profil utilizator": "profile",
    "Comandă nouă": "new_order",
    "Setări proiect": "project_settings",
    "Utilizatori": "users",
    "Verificare date": "data_check",
}

def _logo_data_uri() -> str:
    assets = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    # candidates by name hint
    pats = ["*logo*.png","*logo*.jpg","*logo*.jpeg","*logo*.webp",
            "*kuziini*.png","*kuziini*.jpg","*kuziini*.jpeg","*kuziini*.webp",
            "*insigna*.png","*insigna*.jpg","*insigna*.jpeg","*insigna*.webp"]
    files = []
    for p in pats:
        files.extend(glob.glob(os.path.join(assets, p)))
    files = files or glob.glob(os.path.join(assets, "*.*"))
    if not files:
        return ""
    path = files[0]
    try:
        with open(path, "rb") as fh:
            b = fh.read()
        ext = path.split(".")[-1].lower()
        mime = "image/png" if ext=="png" else ("image/webp" if ext=="webp" else "image/jpeg")
        return f"data:{mime};base64," + base64.b64encode(b).decode("ascii")
    except Exception:
        return ""

def render_header_and_nav(ctx: Dict[str, Any]) -> str:
    today_str = datetime.now().strftime("%A • %d %B %Y")
    data_uri = _logo_data_uri()
    img_html = f'<img src="{data_uri}" alt="Kuziini logo"/>' if data_uri else ""

    st.markdown(
        f"""
        <style>
          :root{{ --hpad: 0px; --b: 1px solid rgba(0,0,0,.10); --r: 8px; }}
          .block-container{{ max-width:100% !important; padding-left:var(--hpad) !important; padding-right:var(--hpad) !important; }}
          [data-testid="stAppViewContainer"]{{ padding-top:0 !important; }}

          .pp-header{{ position:sticky; top:0; z-index:100; background:inherit;
                      margin-left:calc(-1*var(--hpad)); margin-right:calc(-1*var(--hpad)); padding:8px var(--hpad) 6px;
                      border-bottom:1px solid rgba(0,0,0,.06); }}
          .pp-r1{{ position:relative; display:grid; grid-template-columns: 1fr auto 1fr; align-items:center; }}
          .pp-title{{ font-weight:800; font-size:16px; display:inline-flex; gap:.35rem; align-items:center; padding:.18rem .48rem; border:var(--b); border-radius:var(--r); }}
          .pp-center{{ text-align:center; }}
          .pp-center img{{ height:28px; }}
          .pp-date{{ font-size:12px; color:#555; margin-top:2px; }}

          .pp-r1 #pp-account-anchor + div[data-testid="stVerticalBlock"]{{
              position:absolute; right:0; top:50%; transform:translateY(-50%);
              margin:0 !important; padding:0 !important; background:transparent !important; width:max-content;
          }}
          .pp-r1 #pp-account-anchor + div[data-testid="stVerticalBlock"] button{{
              padding:.18rem .48rem !important; border:var(--b) !important; border-radius:var(--r) !important; background:transparent !important;
          }}

          .pp-r2{{ display:flex; justify-content:center; padding:4px 0 6px; }}
          .pp-r2 .stRadio > div{{ gap:0 !important; }}
          .pp-r2 div[role="radiogroup"]{{ display:flex !important; gap:.22rem !important; flex-wrap:nowrap !important; overflow-x:auto; scrollbar-width:thin; margin:0; }}
          .pp-r2 div[role="radiogroup"] label div{{ padding:.16rem .46rem !important; border:1px solid rgba(0,0,0,.15) !important; border-radius:999px !important; font-size:12px !important; line-height:1 !important; white-space:nowrap !important; }}
        </style>
        <div class="pp-header">
          <div class="pp-r1">
            <div class="pp-left">
              <span class="pp-title">Project Planner <span style="opacity:.6">AI Generator</span></span>
            </div>
            <div class="pp-center">
              {img_html}
              <div class="pp-date">{today_str}</div>
            </div>
            <div id="pp-account-anchor"></div>
          </div>
        </div>
        """, unsafe_allow_html=True
    )

    label = (f"👤 {ctx['user'].get('display_name','User')} ▾") if isinstance(ctx.get("user"), dict) else "👤 Cont ▾"
    if hasattr(st, "popover"):
        with st.popover(label, use_container_width=False):
            _account_panel(ctx)
    else:
        with st.expander(label, expanded=False):
            _account_panel(ctx)

    st.markdown('<div class="pp-r2">', unsafe_allow_html=True)
    choice = st.radio("Navigare", list(NAV.keys()), horizontal=True, key="pp_nav", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    return NAV[choice]

def _account_panel(ctx: Dict[str, Any]):
    st.markdown("**Cont utilizator**")
    st.caption(f"Autentificat ca: {ctx['user'].get('email','guest@kuziini.ro')}")
    email = st.text_input("Email", value=ctx['user'].get('email',''), key="pp_email")
    name  = st.text_input("Nume",  value=ctx['user'].get('display_name',''), key="pp_name")
    role  = st.selectbox("Rol", ["owner","project_manager","designer","tehnolog","admin","user","viewer"], index=6, key="pp_role")
    c1, c2, _ = st.columns(3)
    if c1.button("Login/Switch"):
        st.session_state.user = {"email": email or "guest@kuziini.ro", "display_name": name or "Vizitator", "role": role}
        st.rerun()
    if c2.button("Logout"):
        st.session_state.user = {"email": "guest@kuziini.ro", "display_name": "Vizitator", "role": "viewer"}
        st.rerun()

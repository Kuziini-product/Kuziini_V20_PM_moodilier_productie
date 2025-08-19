# streamlit_app.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import streamlit as st

# ---------------- Page config ----------------
st.set_page_config(page_title="Project Planner AI Generator", layout="wide")
APP_ROOT = Path(__file__).resolve().parent

# ---------------- Helpers ----------------
def _find_logo() -> Optional[Path]:
    for p in [
        APP_ROOT / "assets" / "logo.png",
        APP_ROOT / "assets" / "logo_cuzinii.png",
        APP_ROOT / "assets" / "cuzinii_logo.png",
        APP_ROOT / "assets" / "insigna.png",
        APP_ROOT / "logo.png",
    ]:
        if p.exists():
            return p
    return None

def _fallback(msg: str):
    def _r(*_, **__):
        st.info(msg)
    return _r

# ---------------- Containers (nemodificate) ----------------
try:
    from containers import dashboard
except Exception:
    dashboard = type("X",(object,),{"render": staticmethod(_fallback("Dashboard-ul nu este disponibil."))})
try:
    from containers import overview
except Exception:
    overview = type("X",(object,),{"render": staticmethod(_fallback("Vederea generală nu este disponibilă."))})
try:
    from containers import sections
except Exception:
    sections = type("X",(object,),{"render": staticmethod(_fallback("Secțiunile nu sunt disponibile."))})
try:
    from containers import new_order
except Exception:
    new_order = type("X",(object,),{"render": staticmethod(_fallback("Comanda nouă nu este disponibilă."))})
try:
    from containers import users
except Exception:
    users = type("X",(object,),{"render": staticmethod(_fallback("Administrarea utilizatorilor nu este disponibilă."))})
try:
    from containers import user_profile
except Exception:
    user_profile = type("X",(object,),{"render": staticmethod(_fallback("Profilul utilizatorului nu este disponibil."))})
try:
    from containers import data_check
except Exception:
    data_check = type("X",(object,),{"render": staticmethod(_fallback("Verificarea de date va fi disponibilă în curând."))})
try:
    from containers import help
except Exception:
    help = type("X",(object,),{"render": staticmethod(_fallback("Ajutorul nu este disponibil în această versiune."))})

# ---------------- Data ctx ----------------
try:
    from utils import data_loader
    class Ctx: ...
    ctx = Ctx()
    ctx.data = data_loader.data
except Exception:
    ctx = None

# ---------------- Rute (ordine curentă) ----------------
ROUTES = {
    "Dashboard": dashboard.render,
    "Vedere generală": overview.render,
    "Secțiuni": sections.render,
    "Profil utilizator": user_profile.render,
    "Comandă nouă": new_order.render,
    "Utilizatori": users.render,
    "Verificare date": getattr(data_check, "render", _fallback("Verificarea de date ...")),
    "Ajutor": help.render,
}
PAGES = list(ROUTES.keys())

# ---------------- Auth mini ----------------
def _users_df():
    try:
        return ctx.data.users if ctx and hasattr(ctx.data, "users") else None
    except Exception:
        return None

def _set_auth(user: Dict[str, Any] | None):
    if user:
        user["name"] = (user.get("name") or user.get("email") or "Utilizator").strip() or "Utilizator"
    st.session_state["auth"] = user
    if user:
        st.session_state["auth_name"] = user["name"]
        st.session_state["current_user_name"] = user["name"]
    else:
        st.session_state.pop("auth_name", None)
        st.session_state.pop("current_user_name", None)

# ---------------- Style: header card + page card unitar + popover ----------------
st.markdown(
    """
    <style>
      /* Card header (scund) */
      .top-card{
        background:#f7f8ed; border:1px solid #e5e7eb; border-radius:10px;
        padding:.25rem .5rem; margin: .5rem .5rem .6rem .5rem;
      }
      .hdr-row [data-testid="stHorizontalBlock"]{ gap:.45rem !important; }
      .hdr-left{ display:flex; align-items:center; gap:.5rem; min-height:34px; }
      .app-title{ font-weight:800; font-size:1.02rem; margin:0; white-space:nowrap; }
      .badge-pill{
        display:inline-block; padding:.05rem .45rem; border-radius:999px;
        background:#fff; border:1px solid #e5e7eb; font-weight:800; font-size:.72rem;
      }
      .hdr-right{ display:flex; align-items:center; justify-content:flex-end; gap:.45rem; }
      .hdr-date{ color:#6b7280; font-size:.86rem; }
      .auth-mini .avatar{ width:22px; height:22px; border-radius:50%; background:#111827; color:#fff;
                          display:inline-flex; align-items:center; justify-content:center; font-size:.75rem; font-weight:700; }
      .auth-mini .uname{ font-size:.84rem; color:#111827; white-space:nowrap; }
      .auth-mini .stButton>button{
          padding:0 !important; width:22px; height:22px; min-width:22px; border-radius:6px;
          border:1px solid #d1d5db; background:#fff; line-height:20px; font-size:.8rem;
          margin-top:1px;
      }

      /* Bara de navigare */
      .nav-wrap{ padding-top:.2rem; border-top:1px dashed #e5e7eb; margin-top:.25rem; }
      div[role="radiogroup"] > label{ margin-right:.85rem; }

      /* ---- Card pagină: identic pe toate paginile ---- */
      .page-card{
        background:#f7f8ed; border:1px solid #e5e7eb; border-radius:10px;
        padding:.6rem .7rem; margin: 0 .5rem .8rem .5rem;
      }

      /* Dacă vreun container intern își mai desenează încă un card de pagină,
         neutralizăm dublura când e în interiorul cardului global (opțional). */
      .page-card .page-card{ border:0; padding:0; margin:0; background:transparent; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Sidebar diagnostic ----------------
with st.sidebar:
    st.markdown("### 🩺 Diagnostic")
    st.caption("Versiune aplicație: v20")
    st.caption("Logo: " + ("OK" if _find_logo() else "lipsește"))
    st.caption("Autentificat: " + ("DA" if st.session_state.get("auth") else "NU"))

# ---------------- HEADER ÎN CARD ----------------
with st.container():
    st.markdown('<div class="top-card">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.4, 0.7, 2.1], gap="small")
    with c1:
        lp = _find_logo()
        st.markdown('<div class="hdr-left">', unsafe_allow_html=True)
        if lp:
            st.image(str(lp), width=24)
        st.markdown(
            '<span class="app-title">Project Planner AI Generator</span> '
            '<span class="badge-pill">v20</span>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.write("")

    with c3:
        st.markdown('<div class="hdr-right auth-mini">', unsafe_allow_html=True)
        st.markdown(f"<span class='hdr-date'>{datetime.now().strftime('%A • %d %B %Y')}</span>", unsafe_allow_html=True)

        auth = st.session_state.get("auth")
        if auth:
            name = auth.get("name") or auth.get("email") or "User"
            initials = "".join([w[0] for w in name.split()[:2]]).upper() or "U"
            st.markdown(f"<span class='avatar'>{initials}</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='uname'>{name}</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='avatar'>U</span>", unsafe_allow_html=True)
            st.markdown("<span class='uname'>Login</span>", unsafe_allow_html=True)

        # Popover (overlay) — nu împinge layout-ul
        def _auth_panel_content():
            udf = _users_df()
            auth = st.session_state.get("auth")
            if not auth:
                with st.form("login_form_header", clear_on_submit=False):
                    n = st.text_input("Nume", key="login_name_hdr")
                    e = st.text_input("Email", key="login_email_hdr")
                    r1, r2 = st.columns([1, .35], gap="small")
                    with r2:
                        if st.form_submit_button("Login", use_container_width=True):
                            _set_auth({"name": (n or e or "Utilizator").strip(), "email": e.strip()})
                            st.rerun()
            else:
                st.caption("Utilizator activ")
                st.write(auth.get("name") or auth.get("email") or "User")
                rr1, rr2 = st.columns([1,1], gap="small")
                with rr1:
                    if st.button("Logout", key="logout_hdr", use_container_width=True):
                        _set_auth(None)
                        st.rerun()
                with rr2:
                    if udf is not None and not udf.empty:
                        options = udf["name"].astype(str).fillna("").tolist()
                        if "email" in udf.columns:
                            emails = udf["email"].astype(str).fillna("").tolist()
                            options = [o if o else e for o, e in zip(options, emails)]
                        sel = st.selectbox("Schimbă utilizator", options=options, key="switch_user_sel_hdr")
                        if st.button("Switch", key="switch_user_btn_hdr", use_container_width=True):
                            row = udf[udf["name"].astype(str) == sel]
                            if row.empty and "email" in udf.columns:
                                row = udf[udf["email"].astype(str) == sel]
                            user = {"name": sel}
                            for k in ["email", "role", "section", "responsible"]:
                                if k in udf.columns and not row.empty:
                                    user[k] = row.iloc[0][k]
                            _set_auth(user)
                            st.rerun()
                    else:
                        st.caption("Nu există listă de utilizatori pentru switch.")

        if hasattr(st, "popover"):
            with st.popover("▾", use_container_width=False):
                _auth_panel_content()
        else:
            with st.expander("▾", expanded=False):
                _auth_panel_content()

        st.markdown('</div>', unsafe_allow_html=True)

    if "page_key" not in st.session_state:
        st.session_state["page_key"] = "Dashboard"
    nav_index = PAGES.index(st.session_state["page_key"]) if st.session_state["page_key"] in PAGES else 0
    st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
    choice = st.radio("Navigare", PAGES, index=nav_index, horizontal=True,
                      label_visibility="collapsed", key="nav_top_radio")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # /top-card

st.session_state["page_key"] = choice

# ---------------- PAGE WRAPPER: card global pentru orice pagină ----------------
st.markdown('<div class="page-card">', unsafe_allow_html=True)
ROUTES.get(st.session_state["page_key"], dashboard.render)(ctx)
st.markdown('</div>', unsafe_allow_html=True)

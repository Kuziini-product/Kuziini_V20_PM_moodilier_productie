from __future__ import annotations
import os
import streamlit as st

from utils.data_loader import AppData
from containers.nav import render_header_and_nav

import containers.dashboard as dashboard
import containers.overview as overview
import containers.sections as sections
import containers.users as users
import containers.data_check as data_check

def _make_user(email: str = "guest@kuziini.ro", name: str = "Vizitator", role: str = "viewer") -> dict:
    return {"email": email, "display_name": name, "role": role}

def _render_diag_sidebar(ctx):
    with st.sidebar.expander("🔎 Diagnostic", expanded=True):
        st.caption(f"CWD: {os.getcwd()}")
        st.caption(f"assets/logo.png     → {os.path.exists('assets/logo.png')}")
        st.caption(f"data/proiecte.xlsx  → {os.path.exists('data/proiecte.xlsx')}")
        st.caption(f"data/personal.xlsx  → {os.path.exists('data/personal.xlsx')}")
        try:
            diag = ctx["data"].diagnostics()
            notes = diag.get("notes", [])
            if notes:
                st.write("**Note încărcare:**")
                for n in notes: st.write("•", n)
            st.write("**Users**:", diag.get("users_rows"), "rânduri | Col:", ", ".join(diag.get("users_columns", [])))
            st.write("**Projects**:", diag.get("projects_rows"), "rânduri | Col:", ", ".join(diag.get("projects_columns", [])))
        except Exception as e:
            st.error(f"Eroare diagnostic: {e}")

def main():
    st.set_page_config(page_title="Project Planner AI Generator — Kuziini", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")
    if "user" not in st.session_state:
        st.session_state.user = _make_user()
    if "data" not in st.session_state:
        st.session_state.data = AppData()
    ctx = {"user": st.session_state.user, "data": st.session_state.data}
    _render_diag_sidebar(ctx)
    page_key = render_header_and_nav(ctx)

    ROUTES = {
        "dashboard":        dashboard.render,
        "overview":         overview.render,
        "sections":         sections.render,
        "users":            users.render,
        "data_check":       data_check.render,
    }
    # Optional pages if present
    try:
        import containers.profile as profile
        ROUTES["profile"] = profile.render
    except Exception:
        pass
    try:
        import containers.new_order as new_order
        ROUTES["new_order"] = new_order.render
    except Exception:
        pass
    try:
        import containers.project_settings as project_settings
        ROUTES["project_settings"] = project_settings.render
    except Exception:
        pass

    ROUTES.get(page_key, dashboard.render)(ctx)

if __name__ == "__main__":
    main()

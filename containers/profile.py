\
from typing import Dict, Any
import streamlit as st

def render(ctx: Dict[str, Any]):
    user = ctx["user"]
    st.markdown("### 👤 Profil utilizator")
    st.write(f"Nume: **{user.get('display_name')}**  |  Email: `{user.get('email')}`  |  Rol: `{user.get('role')}`")

    st.divider()
    st.markdown("#### Setează progres pe proiect (demo)")
    project = st.selectbox("Alege proiect", ctx["data"].projects["name"])
    pct = st.radio("Status rapid", [25,50,75,100], horizontal=True)
    fine = st.slider("Ajustare fină (%)", 0, 100, pct)
    col1, col2 = st.columns(2)
    if col1.button("Salvează status"):
        st.session_state.setdefault("project_statuses", {})[project] = fine
        st.success(f"Salvat {fine}% pentru {project}")
    if col2.button("Șterge status"):
        st.session_state.setdefault("project_statuses", {}).pop(project, None)
        st.info("Șters.")
    if "project_statuses" in st.session_state:
        st.json(st.session_state["project_statuses"])

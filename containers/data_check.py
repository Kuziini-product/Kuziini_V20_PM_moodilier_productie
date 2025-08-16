from typing import Dict, Any
import streamlit as st
def render(ctx: Dict[str, Any]):
    st.markdown("### 🔎 Verificare date (Excel)")
    diag = ctx["data"].diagnostics()
    with st.expander("Note încărcare / diagnostic", expanded=True):
        notes = diag.get("notes", [])
        if notes:
            for n in notes: st.write("•", n)
        else:
            st.write("Nicio notă.")
    st.divider()
    st.markdown("#### personal.xlsx — primele rânduri")
    st.dataframe(ctx["data"].users.head(10), hide_index=True, use_container_width=True)
    st.markdown("#### proiecte.xlsx — primele rânduri")
    st.dataframe(ctx["data"].projects.head(10), hide_index=True, use_container_width=True)
    st.markdown("#### Secții & progres (extragere)")
    df = ctx["data"].projects[["name","sections","sections_progress","progress_overall"]].copy()
    st.dataframe(df.head(10), hide_index=True, use_container_width=True)

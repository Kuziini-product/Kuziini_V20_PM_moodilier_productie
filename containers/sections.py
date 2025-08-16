\
from typing import Dict, Any
import streamlit as st
from datetime import date

def render(ctx: Dict[str, Any]):
    data = ctx["data"]
    dfp = data.projects
    all_sections = sorted({s for lst in dfp["sections"] for s in (lst or [])})
    if not all_sections:
        st.info("Nu există secții în proiecte. Completează coloana „Dispunere pe secții” în Excel.")
        return

    s = st.selectbox("Alege secția", all_sections)
    mask = dfp["sections"].apply(lambda lst: s in (lst or []))
    df = dfp[mask].copy()
    st.markdown(f"### Proiecte în secția **{s}**")

    def _sec_prog(row):
        m = row.get("sections_progress") or {}
        return m.get(s)
    df["progress_section"] = df.apply(_sec_prog, axis=1)
    st.dataframe(df[["id","name","company","value","progress_section","progress_overall"]], hide_index=True, use_container_width=True)

    st.markdown("#### Detaliu proiect")
    if not df.empty:
        ids = df["id"].tolist()
        pid = st.slider("Selectează proiect", min_value=min(ids), max_value=max(ids), value=ids[0], step=1)
        row = df[df["id"]==pid].iloc[0]
        st.write(f"**{row['name']}** — companie: `{row['company']}` | valoare: **{row['value']}** RON")
        st.progress((row.get("progress_section") or 0)/100.0, text=f"Progres secție {s}: {row.get('progress_section','-')}%")
        st.caption(f"Progres general proiect: {row.get('progress_overall','-')}%")

        st.markdown("##### Responsabili/Participanți secție")
        resp = [u for u in data.get_responsibles_by_section().get(s, [])]
        if resp:
            st.write("**Responsabil(i):** " + ", ".join(resp))
        participants = data.users[data.users["section"]==s]["name"].tolist()
        if participants:
            st.write("**Participanți:** " + ", ".join(participants))

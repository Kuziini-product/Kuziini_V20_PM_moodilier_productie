\
from typing import Dict, Any
import streamlit as st
from datetime import date

def render(ctx: Dict[str, Any]):
    data = ctx["data"]
    dfp = data.projects

    st.markdown("### 🧭 Dashboard — starea curentă")

    projects_total = len(dfp)
    with_dates = dfp.dropna(subset=["start","end"])
    in_progress_today = 0
    if not with_dates.empty:
        t = date.today()
        in_progress_today = int(((with_dates["start"] <= t) & (with_dates["end"] >= t)).sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Proiecte în progres", in_progress_today or projects_total)
    c2.metric("Utilizatori activi", data.users.shape[0])
    c3.metric("Responsabili secții", int((data.users["responsible"]==1).sum()))
    all_sections = sorted({s for lst in dfp["sections"] for s in (lst or [])})
    c4.metric("Secții active", len(all_sections))
    c5.metric("Oferte în curs", len(st.session_state.get("offers", [])))
    late = 0
    if not with_dates.empty:
        late = int((with_dates["end"] < date.today()).sum())
    c6.metric("Proiecte întârziate", late)

    st.divider()
    st.markdown("#### Proiecte — distribuție pe secții")
    counts = {}
    for lst in dfp["sections"]:
        for s in (lst or []):
            counts[s] = counts.get(s, 0) + 1
    if counts:
        st.bar_chart(counts)
    else:
        st.info("Nu există încă secții în datele proiectelor.")

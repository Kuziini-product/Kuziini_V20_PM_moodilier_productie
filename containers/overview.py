\
from typing import Dict, Any
import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

def render(ctx: Dict[str, Any]):
    df = ctx["data"].projects.copy()
    st.markdown("### 📈 Vedere generală — pipeline pe zile")

    if "start" in df.columns and "end" in df.columns and df["start"].notna().any() and df["end"].notna().any():
        today = date.today()
        def color_row(row):
            if pd.isna(row["end"]): return "green"
            if row["end"] < today:
                return "red" if (today - row["end"]).days > 3 else "orange"
            return "green"

        df["color"] = df.apply(color_row, axis=1)
        df["start_ts"] = pd.to_datetime(df["start"])
        df["end_ts"]   = pd.to_datetime(df["end"])

        bars = alt.Chart(df).mark_bar().encode(
            x=alt.X("start_ts:T", title=""),
            x2="end_ts:T",
            y=alt.Y("name:N", sort="-x", title="Proiect"),
            color=alt.Color("color:N", scale=alt.Scale(domain=["green","orange","red"], range=["#4caf50","#ffb300","#e53935"]), legend=None),
            tooltip=["name","company","contact_name","start","end","progress_overall"]
        ).properties(height=320)

        rule = alt.Chart(pd.DataFrame({"today":[pd.to_datetime(today)]})).mark_rule(strokeDash=[6,4]).encode(x="today:T")
        st.altair_chart(bars + rule, use_container_width=True)
    else:
        st.info("Nu există coloane de dată (Start/Final) în Excel. Afișez tabelul proiectelor.")
        st.dataframe(df[["id","name","company","contact_name","value","progress_overall"]], hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("#### Rate tranșe (calcul din procent × valoare)")
    cols = ["name","value","inst1","inst1_amount","inst2","inst2_amount","inst3","inst3_amount","inst4","inst4_amount"]
    st.dataframe(df[cols], hide_index=True, use_container_width=True)

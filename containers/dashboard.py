# containers/dashboard.py
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from utils.data_loader import data

APP_ROOT = Path(__file__).resolve().parents[1]

# ---------- Helpers ----------
def _normalize_projects(dfp: Optional[pd.DataFrame]) -> pd.DataFrame:
    if dfp is None:
        return pd.DataFrame(columns=["id","name","company","start","end","sections","sections_progress","progress_overall","notes"])
    df = dfp.copy()
    for c in ["id","name","company","start","end","sections","sections_progress","progress_overall","notes"]:
        if c not in df.columns:
            df[c] = "" if c not in ("progress_overall",) else 0.0
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df["progress_overall"] = pd.to_numeric(df["progress_overall"], errors="coerce").fillna(0.0)
    return df

def _normalize_users(dfu: Optional[pd.DataFrame]) -> pd.DataFrame:
    if dfu is None:
        return pd.DataFrame(columns=["name","email","section","responsible","role"])
    u = dfu.copy()
    for c in ["name","email","section","responsible","role"]:
        if c not in u.columns:
            u[c] = "" if c != "responsible" else 0
    u["responsible"] = pd.to_numeric(u["responsible"], errors="coerce").fillna(0).astype(int)
    return u

def _explode_sections(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, r in df.iterrows():
        secs = [s.strip() for s in str(r.get("sections","")).split(",") if s.strip()]
        if not secs:
            out.append({"id": r["id"], "section": "(nedefinit)"})
        else:
            for s in secs:
                out.append({"id": r["id"], "section": s})
    return pd.DataFrame(out)

def _risk_bucket(days_late: int) -> str:
    if days_late <= 0:   # înainte sau exact la termen
        return "✅ La termen"
    if 1 <= days_late <= 3:
        return "⚠️ Avertizare (1–3 zile)"
    return "⛔ Critic (>3 zile)"

def _parse_activity(notes: str) -> List[dict]:
    if not notes:
        return []
    lines = [ln.strip() for ln in str(notes).splitlines() if "[UPD]" in ln]
    out = []
    for ln in lines:
        # [UPD][YYYY-mm-dd HH:MM][USER:Name][SEC:Section][ALL:0/1] text | FILES: ...
        try:
            ts = ln.split("][", 2)[1].strip("]")
            when = ts.replace("UPD][","")
            user = ""
            sec = ""
            if "[USER:" in ln:
                user = ln.split("[USER:",1)[1].split("]",1)[0]
            if "[SEC:" in ln:
                sec = ln.split("[SEC:",1)[1].split("]",1)[0]
            msg = ln.split("] ",1)[1] if "] " in ln else ln
            out.append({"when": when, "user": user, "section": sec, "text": msg})
        except Exception:
            out.append({"when":"", "user":"", "section":"", "text": ln})
    return out

# ---------- UI ----------
def render(ctx=None, **kwargs):
    st.markdown("""
    <style>
    .dash-compact [data-testid="stVerticalBlock"]{ gap: .2rem !important; }
    .dash-compact [data-testid="stHorizontalBlock"]{ gap: .4rem !important; }
    .dash-compact .metricbox{border:1px solid #e5e7eb;border-radius:10px;padding:8px;background:#fff;}
    .dash-compact .small{font-size:.85rem;color:#6b7280}
    .dash-compact .tablewrap .row{padding:4px 0;border-bottom:1px dashed #e5e7eb;}
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="dash-compact">', unsafe_allow_html=True)

    

    st.markdown("## 📊 Dashboard — KPI & risc & activitate")

    dfp = _normalize_projects(data.projects.copy())
    dfu = _normalize_users(getattr(data, "users", None))

    if dfp.empty:
        st.warning("Nu există proiecte încărcate.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    today = pd.to_datetime(datetime.now().date())

    # ---------- Filtre ----------
    c1, c2, c3 = st.columns([1.5, 1.2, 1.2])
    with c1:
        # Filtru secție
        all_secs = sorted(set(_explode_sections(dfp)["section"].tolist()))
        sec_sel = st.multiselect("Secții", options=all_secs, default=[])
    with c2:
        start_from = st.date_input("De la", value=today - pd.Timedelta(days=14))
    with c3:
        end_to = st.date_input("Până la", value=today + pd.Timedelta(days=42))

    # aplicăm filtre
    f = dfp.copy()
    if sec_sel:
        ex = _explode_sections(f)
        keep_ids = ex[ex["section"].isin(sec_sel)]["id"].astype(str).unique().tolist()
        f = f[f["id"].astype(str).isin(keep_ids)]
    if start_from:
        f = f[(f["end"].isna()) | (f["end"] >= pd.to_datetime(start_from))]
    if end_to:
        f = f[(f["start"].isna()) | (f["start"] <= pd.to_datetime(end_to))]

    # ---------- KPI sus ----------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='metricbox'>", unsafe_allow_html=True)
        st.metric("Proiecte active", int((f["progress_overall"] < 100).sum()))
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='metricbox'>", unsafe_allow_html=True)
        ex = _explode_sections(f)
        st.metric("Secții implicate", int(ex["section"].nunique()) if not ex.empty else 0)
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='metricbox'>", unsafe_allow_html=True)
        st.metric("Utilizatori (total)", int(dfu.shape[0]))
        st.markdown("</div>", unsafe_allow_html=True)
    with c4:
        st.markdown("<div class='metricbox'>", unsafe_allow_html=True)
        overdue = f[(~f["end"].isna()) & (today > f["end"]) & (f["progress_overall"] < 100)]
        st.metric("Proiecte întârziate", int(overdue.shape[0]))
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- Semafor risc ----------
    st.subheader("Semafor risc (după termenul de finalizare)")
    tmp = f.copy()
    tmp["days_late"] = (today - tmp["end"]).dt.days
    tmp["days_late"] = tmp["days_late"].fillna(-9999)
    tmp["bucket"] = tmp["days_late"].apply(lambda x: _risk_bucket(int(x)) if x != -9999 else "– fără termen –")
    agg = tmp.groupby("bucket", dropna=False)["id"].count().reset_index().rename(columns={"id":"count"}).sort_values("count", ascending=False)
    c1, c2 = st.columns([1.4, 2.6])
    with c1:
        st.dataframe(agg, hide_index=True, use_container_width=True)
    with c2:
        # top 6 la risc (cu termen depășit și progres < 100)
        top = tmp[(tmp["days_late"] > 0) & (tmp["progress_overall"] < 100)].copy()
        top = top.assign(days_late=top["days_late"].astype(int)).sort_values(["days_late","end"], ascending=[False, True]).head(6)
        view = top[["id","name","company","end","days_late","progress_overall"]]
        st.dataframe(view, hide_index=True, use_container_width=True)

    # ---------- Distribuție pe secții ----------
    st.subheader("Distribuție pe secții (proiecte care ating secția)")
    ex_all = _explode_sections(f)
    if ex_all.empty:
        st.caption("Nu există secții înregistrate.")
    else:
        counts = ex_all.groupby("section")["id"].nunique().reset_index().rename(columns={"id":"proiecte"})
        counts = counts.sort_values("proiecte", ascending=False)
        st.bar_chart(counts, x="section", y="proiecte", height=220)

    # ---------- Prognoză 6 săptămâni (proiecte cu deadline în interval) ----------
    st.subheader("Prognoză finalizări (următoarele 6 săptămâni)")
    horizon = today + pd.Timedelta(days=42)
    g = f[(~f["end"].isna()) & (f["end"].between(today, horizon))].copy()
    if g.empty:
        st.caption("Nu există finalizări programate în interval.")
    else:
        g["week"] = g["end"].dt.to_period("W-SUN").dt.start_time.dt.date
        per_week = g.groupby("week")["id"].nunique().reset_index().rename(columns={"id":"proiecte"})
        st.line_chart(per_week, x="week", y="proiecte", height=220)

    # ---------- Activitate recentă ----------
    st.subheader("Ultimele activități")
    acts = []
    for _, r in f.iterrows():
        for a in _parse_activity(r.get("notes","")):
            acts.append({
                "when": a["when"],
                "project": r.get("name",""),
                "section": a.get("section",""),
                "user": a.get("user",""),
                "text": a.get("text",""),
            })
    if acts:
        act_df = pd.DataFrame(acts)
        # ordonăm desc după timp dacă se poate parsa
        try:
            act_df["_ts"] = pd.to_datetime(act_df["when"], errors="coerce")
            act_df = act_df.sort_values("_ts", ascending=False)
            act_df = act_df.drop(columns=["_ts"])
        except Exception:
            pass
        st.dataframe(act_df.head(15), hide_index=True, use_container_width=True)
    else:
        st.caption("Nu există activitate înregistrată încă.")

    st.markdown("</div>", unsafe_allow_html=True)

# containers/overview.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
PROJECTS_XLSX = DATA_DIR / "proiecte.xlsx"
PERSONAL_XLSX = DATA_DIR / "personal.xlsx"

SHEET_PROJECTS = "Proiecte"
SHEET_PERSONAL = "Personal"

# Coloane de bază pe care le afișăm; dacă lipsesc, le completăm cu valori goale
BASE_COLS = [
    "id", "name", "company", "responsible", "participants",
    "value", "status", "progress_overall", "start", "end", "sections"
]

@st.cache_data(show_spinner=False)
def load_df(path: Path, sheet: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Eroare la citirea «{path.name}» / foaia «{sheet}»: {e}")
        return pd.DataFrame()

def normalize_projects(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # Asigurăm coloanele așteptate
    for c in BASE_COLS:
        if c not in df.columns:
            df[c] = None

    # Tipuri sigure
    df["progress_overall"] = pd.to_numeric(df["progress_overall"], errors="coerce")
    df["status"] = pd.to_numeric(df["status"], errors="coerce")

    for c in ("start", "end"):
        df[c] = pd.to_datetime(df[c], errors="coerce")

    # “sections” / “participants” ca string
    df["sections"] = df["sections"].fillna("").astype(str)
    df["participants"] = df["participants"].fillna("").astype(str)

    # “value” numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Chei de sortare dedicate (evităm erori de tip)
    df["__end_dt"] = df["end"]
    df["__status_num"] = df["status"].fillna(-1)
    df["__prog_num"] = df["progress_overall"].fillna(-1)

    return df

def render(ctx=None, **kwargs):
    st.markdown("## 📚 Vedere generală")
    st.caption("Registru proiecte cu filtre. Compatibil cu «participants», «section_deadlines» și lista extinsă de secții.")

    dfp = load_df(PROJECTS_XLSX, SHEET_PROJECTS)
    dfu = load_df(PERSONAL_XLSX, SHEET_PERSONAL)

    if dfp.empty:
        st.warning("Nu am găsit proiecte (data/proiecte.xlsx).")
        return

    df = normalize_projects(dfp.copy())

    # ==== Filtre ====
    left, mid, right = st.columns(3)
    with left:
        opt_client = ["(toți)"] + sorted(df["company"].dropna().astype(str).unique().tolist())
        client = st.selectbox("Client", opt_client, index=0)
    with mid:
        opt_resp = ["(toți)"] + sorted(df["responsible"].dropna().astype(str).unique().tolist())
        resp = st.selectbox("Responsabil", opt_resp, index=0)
    with right:
        all_secs = sorted({s.strip() for row in df["sections"] for s in row.split(",") if s.strip()})
        opt_sec = ["(toate)"] + all_secs
        sec = st.selectbox("Secție", opt_sec, index=0)

    f = df
    if client != "(toți)":
        f = f[f["company"].astype(str) == client]
    if resp != "(toți)":
        f = f[f["responsible"].astype(str) == resp]
    if sec != "(toate)":
        # IMPORTANT: fără regex -> nu mai cade pe paranteze / simboluri
        f = f[f["sections"].astype(str).str.contains(sec, regex=False, na=False)]

    # ==== Tabel ====
    table_cols = [
        "id", "name", "company", "responsible",
        "progress_overall", "status", "start", "end",
        "sections", "participants", "value"
    ]
    for c in table_cols:
        if c not in f.columns:
            f[c] = None

    # Sortare robustă (după end, apoi status, apoi progres)
    f_sorted = f.sort_values(
        by=["__end_dt", "__status_num", "__prog_num"],
        ascending=[True, False, False],
        kind="mergesort"  # stabil
    )

    # Afișăm datele prietenește (date fără timp)
    out = f_sorted.copy()
    out["start"] = pd.to_datetime(out["start"], errors="coerce").dt.date
    out["end"] = pd.to_datetime(out["end"], errors="coerce").dt.date

    st.dataframe(out[table_cols], use_container_width=True)

    # ==== KPI ====
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Proiecte", len(out))
    k2.metric("Progres mediu", float(out["progress_overall"].mean(skipna=True).round(1)) if len(out) else 0.0)
    k3.metric("Valoare totală", float(out["value"].sum(skipna=True)) if len(out) else 0.0)
    now = pd.Timestamp.now(tz=None)
    active_mask = (pd.to_datetime(out["start"], errors="coerce") <= now) & (pd.to_datetime(out["end"], errors="coerce") >= now)
    k4.metric("În lucru acum", int(active_mask.sum()))

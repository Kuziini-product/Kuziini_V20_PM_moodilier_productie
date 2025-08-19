
# containers/data_check.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
PROJECTS_XLSX = DATA_DIR / "proiecte.xlsx"
PERSONAL_XLSX = DATA_DIR / "personal.xlsx"

SHEET_PROJECTS = "Proiecte"
SHEET_PERSONAL = "Personal"

ALLOWED_SECTIONS = ["Ofertare", "Proiectare & Design", "Tehnologică", "Achiziții", "CNC", "Debitare", "Furnir", "Pregătire vopsitorie", "Vopsitorie", "Asamblare", "CTC", "Ambalare", "Transport (Livrare)", "Montaj"]

CRITICAL_PROJECT_COLS = ["id","name","company","value","start","end","status","progress_overall"]
RECOMM_PROJECT_COLS = [
    "contact_name","contact_email","contact_phone","address","floor","install_contact",
    "responsible","participants",
    "sections","sections_progress","section_deadlines",
    "inst1","inst2","inst3","inst4","inst1_amount","inst2_amount","inst3_amount","inst4_amount",
    "notes"
]
CRITICAL_PERSON_COLS = ["name","email","role","section","is_primary"]
DATE_COLS = ["start","end"]

def _safe_read_excel(path: Path, sheet: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    except Exception as e:
        st.error(f"Nu pot citi fișierul: `{path.name}` foaia `{sheet}`. Detalii: {e}")
        return pd.DataFrame()

def _to_date(series: pd.Series):
    try:
        return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.to_datetime(pd.Series([None]*len(series)))

def _list_missing(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c not in df.columns]

def validate_projects(df_projects: pd.DataFrame, df_personal: pd.DataFrame) -> dict:
    res = {"errors": [], "warnings": [], "metrics": {}}
    if df_projects.empty:
        res["errors"].append("Foaia «Proiecte» este goală sau nu a putut fi citită."); return res

    missing_crit = _list_missing(df_projects, CRITICAL_PROJECT_COLS)
    if missing_crit: res["errors"].append("Lipsesc coloane critice în «Proiecte»: " + ", ".join(missing_crit))
    missing_reco = _list_missing(df_projects, RECOMM_PROJECT_COLS)
    if missing_reco: res["warnings"].append("Lipsesc coloane recomandate în «Proiecte»: " + ", ".join(missing_reco))

    if "id" in df_projects.columns:
        dup_mask = df_projects["id"].astype(str).str.strip().duplicated(keep=False)
        if dup_mask.any():
            res["errors"].append("ID-uri duplicate: " + ", ".join(df_projects.loc[dup_mask, "id"].astype(str).tolist()))

    for c in [c for c in CRITICAL_PROJECT_COLS if c in df_projects.columns]:
        n = df_projects[c].isna().sum()
        if n>0: res["errors"].append(f"«{c}» are {n} valori lipsă.")

    if "progress_overall" in df_projects.columns:
        prog = pd.to_numeric(df_projects["progress_overall"], errors="coerce")
        bad = df_projects[(prog<0) | (prog>100) | prog.isna()]
        if not bad.empty: res["errors"].append("«progress_overall» în afara [0..100] pentru: " + ", ".join(bad.get("id", bad.index).astype(str)))

    for c in DATE_COLS:
        if c in df_projects.columns:
            df_projects[c] = _to_date(df_projects[c])
    if "start" in df_projects.columns and "end" in df_projects.columns:
        bad = df_projects[df_projects["start"] > df_projects["end"]]
        if not bad.empty:
            res["errors"].append("Date inversate (start > end) pentru: " + ", ".join(bad.get("id", bad.index).astype(str)))
        today = pd.to_datetime(datetime.now().date())
        if "progress_overall" in df_projects.columns:
            prog = pd.to_numeric(df_projects["progress_overall"], errors="coerce").fillna(0)
            late = df_projects[(df_projects["end"] < today) & (prog < 100)]
            if not late.empty:
                res["warnings"].append("Proiecte întârziate: " + ", ".join(late.get("id", late.index).astype(str)))

    if "responsible" in df_projects.columns and not df_personal.empty:
        names = set(df_personal.get("name", pd.Series([], dtype=str)).astype(str).str.strip())
        miss = df_projects[~df_projects["responsible"].astype(str).str.strip().isin(names)]
        if not miss.empty:
            res["warnings"].append("Responsabili inexistenți în «Personal» pentru: " + ", ".join(miss.get("id", miss.index).astype(str)))

    if "participants" in df_projects.columns and not df_personal.empty:
        known = set(df_personal["name"].astype(str))
        unk = []
        for _, row in df_projects.iterrows():
            part = str(row.get("participants","")).strip()
            if not part: continue
            lst = [x.strip() for x in part.split(",") if x.strip()]
            for n in lst:
                if n not in known:
                    unk.append(str(row.get("id","?")) + ":" + n)
        if unk:
            res["warnings"].append("Participanți necunoscuți (nu apar în «Personal»): " + ", ".join(unk))

    if "sections" in df_projects.columns:
        bad_rows = []
        for _, row in df_projects.iterrows():
            lst = [x.strip() for x in str(row["sections"]).split(",") if x.strip()]
            for s in lst:
                if s not in ALLOWED_SECTIONS:
                    bad_rows.append(str(row.get("id","?")) + ":" + s)
        if bad_rows:
            res["errors"].append("Secții invalide față de nomenclator: " + ", ".join(bad_rows))

    res["metrics"] = {
        "rows_projects": len(df_projects),
        "rows_personal": len(df_personal),
        "delayed": int(((df_projects.get("end") < pd.to_datetime(datetime.now().date())) & (pd.to_numeric(df_projects.get("progress_overall",0), errors="coerce")<100)).sum()) if not df_projects.empty else 0
    }
    return res

def validate_personal(df_personal: pd.DataFrame) -> dict:
    res = {"errors": [], "warnings": []}
    if df_personal.empty:
        res["errors"].append("Foaia «Personal» este goală."); return res
    missing = _list_missing(df_personal, CRITICAL_PERSON_COLS)
    if missing: res["errors"].append("Lipsesc coloane critice în «Personal»: " + ", ".join(missing))
    if "email" in df_personal.columns:
        bad = df_personal[~df_personal["email"].astype(str).str.contains("@", na=False)]
        if not bad.empty: res["warnings"].append("Emailuri potențial invalide la rândurile: " + ", ".join(map(str,bad.index.tolist())))
    return res

def render(ctx=None, **kwargs) -> None:
    st.markdown("## 🩺 Diagnoză date")
    st.caption("Verifică integritatea fișierelor Excel (structură actualizată).")

    c1,c2,c3 = st.columns(3)
    c1.metric("proiecte.xlsx", "există" if PROJECTS_XLSX.exists() else "lipsește")
    c2.metric("personal.xlsx", "există" if PERSONAL_XLSX.exists() else "lipsește")
    c3.metric("Folder data", str(DATA_DIR.name))

    df_projects = _safe_read_excel(PROJECTS_XLSX, SHEET_PROJECTS) if PROJECTS_XLSX.exists() else pd.DataFrame()
    df_personal = _safe_read_excel(PERSONAL_XLSX, SHEET_PERSONAL) if PERSONAL_XLSX.exists() else pd.DataFrame()

    with st.expander("📄 Mostră «Proiecte» (primele 10 rânduri)", expanded=False):
        st.dataframe(df_projects.head(10), use_container_width=True)
    with st.expander("👤 Mostră «Personal» (primele 10 rânduri)", expanded=False):
        st.dataframe(df_personal.head(10), use_container_width=True)

    proj_res = validate_projects(df_projects, df_personal)
    pers_res = validate_personal(df_personal)

    warn_count = len(proj_res["warnings"]) + len(pers_res["warnings"])
    err_count = len(proj_res["errors"]) + len(pers_res["errors"])

    st.info("Structură secții (actuală): " + ", ".join(ALLOWED_SECTIONS))

    if err_count == 0: st.success("Nu s-au găsit erori critice.")
    else: st.error(f"S-au găsit {err_count} erori critice.")

    if warn_count == 0: st.info("Nu s-au găsit avertizări.")
    else: st.warning(f"S-au găsit {warn_count} avertizări.")

    m = proj_res.get("metrics", {})
    m1,m2,m3 = st.columns(3)
    m1.metric("Proiecte (rânduri)", m.get("rows_projects", len(df_projects)))
    m2.metric("Personal (rânduri)", m.get("rows_personal", len(df_personal)))
    m3.metric("Proiecte întârziate", m.get("delayed", 0))

    with st.expander("❌ Erori critice", expanded=err_count>0):
        if err_count==0: st.caption("Nicio eroare critică.")
        else:
            for e in proj_res["errors"]: st.error(e)
            for e in pers_res["errors"]: st.error(e)

    with st.expander("⚠️ Avertizări", expanded=warn_count>0):
        if warn_count==0: st.caption("Nicio avertizare.")
        else:
            for w in proj_res["warnings"]: st.warning(w)
            for w in pers_res["warnings"]: st.warning(w)

    st.markdown("---")
    st.caption("Diagnoza nu modifică fișierele.")

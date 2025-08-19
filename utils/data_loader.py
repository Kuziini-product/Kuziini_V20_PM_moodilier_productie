# utils/data_loader.py
from __future__ import annotations
"""
Data Loader unificat pentru Project Planner v20.

– NU face aritmetică pe 'id' (evită TypeError).
– Parsează date ISO (YYYY-MM-DD) fără warnings (cu fallback tolerant).
– Garantează coloanele standard pentru «Proiecte» și «Personal».
– Expune clasa **AppData** (cum o importă aplicația) + alias **DataLoader = AppData**.
– Alias-uri: **data.users** (=> personal).
– **diagnostics()** este METODĂ (apelabilă) + proprietate **diagnostics_data** dacă vrei dict direct.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import pandas as pd

# --- Căi & foi ----------------------------------------------------------------
APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"

PROJECTS_XLSX = DATA_DIR / "proiecte.xlsx"
PERSONAL_XLSX = DATA_DIR / "personal.xlsx"

SHEET_PROJECTS = "Proiecte"
SHEET_PERSONAL = "Personal"

# --- Nomenclator secții -------------------------------------------------------
SECTIONS: List[str] = [
    "Ofertare",
    "Proiectare & Design",
    "Tehnologică",
    "Achiziții",
    "CNC",
    "Debitare",
    "Furnir",
    "Pregătire vopsitorie",
    "Vopsitorie",
    "Asamblare",
    "CTC",
    "Ambalare",
    "Transport (Livrare)",
    "Montaj",
]

# --- Ordine/coloane standard --------------------------------------------------
PROJECT_COLS_ORDER: List[str] = [
    "id", "name", "company",
    "contact_name", "contact_email", "contact_phone",
    "address", "floor", "install_contact",
    "responsible", "participants",
    "value",
    "inst1", "inst2", "inst3", "inst4",
    "inst1_amount", "inst2_amount", "inst3_amount", "inst4_amount",
    "sections", "sections_progress", "section_deadlines",
    "progress_overall", "status",
    "start", "end",
    "notes",
]

PERSON_COLS_ORDER: List[str] = [
    "name", "email", "phone", "role", "section", "is_primary",
]

# --- Utilitare interne ---------------------------------------------------------
def _safe_read_excel(path: Path, sheet: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    except Exception:
        return pd.DataFrame()

def ensure_project_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in PROJECT_COLS_ORDER:
        if c not in df.columns:
            df[c] = None
    return df

def ensure_person_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in PERSON_COLS_ORDER:
        if c not in df.columns:
            df[c] = None
    return df

def _parse_date_iso(series: pd.Series) -> pd.Series:
    # Întâi încercăm strict ISO
    s = pd.to_datetime(series, errors="coerce", format="%Y-%m-%d")
    # Fallback tolerant dacă în celule apar alte formate
    mask = s.isna() & series.notna()
    if mask.any():
        s2 = pd.to_datetime(series[mask], errors="coerce", dayfirst=True)
        s.loc[mask] = s2
    return s.dt.date

def _normalize_projects(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df = pd.DataFrame(columns=PROJECT_COLS_ORDER)
    df = ensure_project_columns(df.copy())

    # id ca string (NU facem aritmetică pe el)
    df["id"] = df["id"].apply(lambda v: None if pd.isna(v) else str(v).strip())

    # text
    for c in [
        "name","company","contact_name","contact_email","contact_phone",
        "address","install_contact","responsible","participants",
        "sections","sections_progress","section_deadlines","notes",
    ]:
        df[c] = df[c].astype(str).where(~df[c].isna(), None)
        df[c] = df[c].apply(lambda v: None if v in {"nan","None"} else v)

    # numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["status"] = pd.to_numeric(df["status"], errors="coerce")
    df["progress_overall"] = pd.to_numeric(df["progress_overall"], errors="coerce")
    for c in ("inst1_amount","inst2_amount","inst3_amount","inst4_amount"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # flags tranșe ('da'/'nu')
    for c in ("inst1","inst2","inst3","inst4"):
        if c in df.columns:
            df[c] = df[c].apply(lambda v: "da" if str(v).strip().lower() in {"1","true","da","yes"} else "nu")

    df["floor"] = pd.to_numeric(df["floor"], errors="coerce").astype("Int64")

    # date
    df["start"] = _parse_date_iso(df["start"])
    df["end"]   = _parse_date_iso(df["end"])

    return df[PROJECT_COLS_ORDER]

def _normalize_personal(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df = pd.DataFrame(columns=PERSON_COLS_ORDER)
    df = ensure_person_columns(df.copy())

    for c in ("name","email","role","section"):
        df[c] = df[c].astype(str).str.strip()
    df["phone"] = df["phone"].astype(str).str.strip()
    df["is_primary"] = pd.to_numeric(df["is_primary"], errors="coerce").fillna(0).astype(int)

    return df[PERSON_COLS_ORDER]

# --- Parseri utili pe proiect -------------------------------------------------
def split_sections(sections_field: Union[str, float, None]) -> List[str]:
    if pd.isna(sections_field) or not str(sections_field).strip():
        return []
    raw = [s.strip() for s in str(sections_field).split(",") if s.strip()]
    return [s for s in SECTIONS if s in raw]

def parse_section_progress(progress_field: Union[str, float, None]) -> List[int]:
    if pd.isna(progress_field) or not str(progress_field).strip():
        return []
    vals: List[int] = []
    for x in str(progress_field).split(","):
        x = x.strip()
        if not x:
            continue
        try:
            vals.append(int(float(x)))
        except Exception:
            vals.append(0)
    return vals

def parse_section_deadlines(deadlines_field: Union[str, float, None]) -> Dict[str, Optional[pd.Timestamp]]:
    out: Dict[str, Optional[pd.Timestamp]] = {}
    if pd.isna(deadlines_field) or not str(deadlines_field).strip():
        return out
    parts = [p.strip() for p in str(deadlines_field).split(";") if p.strip()]
    for p in parts:
        if ":" not in p:
            continue
        sec, d = p.split(":", 1)
        out[sec.strip()] = pd.to_datetime(d.strip(), errors="coerce")
    return out

def filter_projects_by_section(df: pd.DataFrame, section: str) -> pd.DataFrame:
    if not section:
        return df
    return df[df["sections"].astype(str).str.contains(section, regex=False, na=False)].copy()

# --- Clasa cerută de app: AppData (cu alias DataLoader) -----------------------
@dataclass
class _Cache:
    projects: Optional[pd.DataFrame] = None
    personal: Optional[pd.DataFrame] = None

class AppData:
    """Loader cu cache intern; folosit în tot proiectul."""
    def __init__(self) -> None:
        self._cache = _Cache()

    @property
    def projects(self) -> pd.DataFrame:
        if self._cache.projects is None:
            self._cache.projects = self._load_projects()
        return self._cache.projects

    @property
    def personal(self) -> pd.DataFrame:
        if self._cache.personal is None:
            self._cache.personal = self._load_personal()
        return self._cache.personal

    # Alias compatibil cerut de Dashboard: data.users
    @property
    def users(self) -> pd.DataFrame:
        return self.personal

    # Proprietate pentru citire directă (fără paranteze), dacă e nevoie
    @property
    def diagnostics_data(self) -> Dict[str, Any]:
        return self._compute_diagnostics()

    # *** IMPORTANT: metoda apelabilă așteptată de sidebar ***
    def diagnostics(self) -> Dict[str, Any]:
        return self._compute_diagnostics()

    # Alias dacă e apelată altfel
    def get_diagnostics(self) -> Dict[str, Any]:
        return self._compute_diagnostics()

    def refresh(self) -> None:
        self._cache = _Cache()

    # --- intern ---------------------------------------------------------------
    def _load_projects(self) -> pd.DataFrame:
        df = _safe_read_excel(PROJECTS_XLSX, SHEET_PROJECTS)
        return _normalize_projects(df)

    def _load_personal(self) -> pd.DataFrame:
        df = _safe_read_excel(PERSONAL_XLSX, SHEET_PERSONAL)
        return _normalize_personal(df)

    def _compute_diagnostics(self) -> Dict[str, Any]:
        """Agregă informațiile folosite în panoul din stânga."""
        try:
            logo_ok = (APP_ROOT / "assets" / "logo.png").exists()
        except Exception:
            logo_ok = False

        proj_ok = PROJECTS_XLSX.exists()
        pers_ok = PERSONAL_XLSX.exists()

        dfp = self.projects
        dfu = self.personal

        # KPI ușoare
        today = pd.Timestamp.today()
        start_dt = pd.to_datetime(dfp.get("start"), errors="coerce") if not dfp.empty else pd.Series([], dtype="datetime64[ns]")
        end_dt   = pd.to_datetime(dfp.get("end"), errors="coerce") if not dfp.empty else pd.Series([], dtype="datetime64[ns]")
        active = int(((start_dt <= today) & (end_dt >= today)).sum()) if not dfp.empty else 0

        sections_active = 0
        if not dfp.empty and "sections" in dfp.columns:
            tokens = {s.strip() for row in dfp["sections"].fillna("") for s in str(row).split(",") if s.strip()}
            sections_active = len(tokens)

        missing_proj_crit = [c for c in ["id","name","company","value","start","end","status","progress_overall"] if c not in dfp.columns]
        diagnostics = {
            "cwd": str(APP_ROOT),
            "files": {
                "assets/logo.png": logo_ok,
                "data/proiecte.xlsx": proj_ok,
                "data/personal.xlsx": pers_ok,
            },
            "counts": {
                "projects_rows": int(len(dfp)),
                "users_rows": int(len(dfu)),
                "projects_active_now": active,
                "sections_active": sections_active,
            },
            "project_missing_critical_cols": missing_proj_crit,
        }
        return diagnostics

# alias de compatibilitate
DataLoader = AppData
data = AppData()  # singleton

# --- Alias-uri funcționale ----------------------------------------------------
def get_projects() -> pd.DataFrame:
    return data.projects

def get_personal() -> pd.DataFrame:
    return data.personal

def get_users() -> pd.DataFrame:
    return data.users

def reload_data() -> None:
    data.refresh()

# --- KPI simple ---------------------------------------------------------------
def kpi_summary(df: pd.DataFrame) -> Dict[str, Union[int, float]]:
    if df.empty:
        return {"count": 0, "progress_avg": 0.0, "value_sum": 0.0, "active_now": 0}
    today = pd.Timestamp.today()
    progress_avg = float(pd.to_numeric(df["progress_overall"], errors="coerce").mean(skipna=True) or 0.0)
    value_sum = float(pd.to_numeric(df["value"], errors="coerce").sum(skipna=True) or 0.0)
    start_dt = pd.to_datetime(df["start"], errors="coerce")
    end_dt = pd.to_datetime(df["end"], errors="coerce")
    active = ((start_dt <= today) & (end_dt >= today)).sum()
    return {
        "count": int(len(df)),
        "progress_avg": round(progress_avg, 1),
        "value_sum": round(value_sum, 2),
        "active_now": int(active),
    }

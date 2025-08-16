
from __future__ import annotations
import os, re, glob
import pandas as pd
from datetime import timedelta, date
from typing import Dict, List, Any, Optional, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _split_list(s: str) -> List[str]:
    if not isinstance(s, str): return []
    parts = re.split(r"[;,/|]+", s)
    return [p.strip() for p in parts if p.strip()]

def _parse_money(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip()
    if not s: return None
    s = re.sub(r"[^\d,.-]", "", s)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def _parse_pct(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip()
    if not s: return None
    s = s.replace("%","").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def _parse_kv_list(s: str) -> Dict[str, float]:
    if not isinstance(s, str): return {}
    items = re.split(r"[;,]+", s)
    out: Dict[str, float] = {}
    for it in items:
        if "=" in it:
            k, v = it.split("=", 1)
        elif ":" in it:
            k, v = it.split(":", 1)
        else:
            continue
        p = _parse_pct(v)
        if p is not None:
            out[k.strip()] = p
    return out

# ---------- Auto-detection helpers ----------
def _score_projects_header(cols: List[str]) -> int:
    keys = ["proiect","compan","persoan","email","etaj","valoare","transa","tranșa","dispunere","progres","start","final","dead"]
    s = 0
    low = [c.lower() for c in cols]
    for k in keys:
        if any(k in c for c in low): s += 1
    return s

def _score_users_header(cols: List[str]) -> int:
    keys = ["nume","email","sec","respons","rol"]
    s = 0
    low = [c.lower() for c in cols]
    for k in keys:
        if any(k in c for c in low): s += 1
    return s

def _pick_best_sheet(xl: pd.ExcelFile, mode: str) -> str:
    best_name, best_score = xl.sheet_names[0], -1
    for sh in xl.sheet_names:
        try:
            tmp = xl.parse(sheet_name=sh, nrows=3)
            cols = list(tmp.columns)
            score = _score_projects_header(cols) if mode=="projects" else _score_users_header(cols)
            if score > best_score:
                best_score, best_name = score, sh
        except Exception:
            continue
    return best_name

def _find_excel_path(kind: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (file_path, sheet_name). kind in {'projects','users'}"""
    if not os.path.isdir(DATA_DIR):
        return None, None
    files = glob.glob(os.path.join(DATA_DIR, "*.xlsx"))
    # preferred name hints
    if kind == "projects":
        prefer = ["proiect", "project", "proiecte"]
    else:
        prefer = ["personal", "users", "utilizator", "utilizatori"]
    # try prefer first
    ranked = sorted(files, key=lambda p: 0 if any(h in os.path.basename(p).lower() for h in prefer) else 1)
    for path in ranked if ranked else files:
        try:
            xl = pd.ExcelFile(path, engine="openpyxl")
            sheet = _pick_best_sheet(xl, "projects" if kind=="projects" else "users")
            return path, sheet
        except Exception:
            continue
    return (files[0], None) if files else (None, None)

class AppData:
    def __init__(self):
        self._users: Optional[pd.DataFrame] = None
        self._projects: Optional[pd.DataFrame] = None
        self.last_notes: List[str] = []

    def _note(self, msg: str) -> None:
        self.last_notes.append(msg)

    # USERS
    @property
    def users(self) -> pd.DataFrame:
        if self._users is None:
            self._users = self._load_users()
        return self._users

    def _load_users(self) -> pd.DataFrame:
        fpath, sheet = _find_excel_path("users")
        df = pd.DataFrame()
        if fpath:
            try:
                df = pd.read_excel(fpath, sheet_name=sheet, engine="openpyxl")
                self._note(f"Loaded {os.path.basename(fpath)} (sheet: {sheet}) — {df.shape[0]} rânduri.")
            except Exception as e:
                self._note(f"Eroare citire {os.path.basename(fpath)}: {e!r}. Folosesc demo.")
        else:
            self._note("Nu am găsit fișierul de utilizatori în /data (ex: personal.xlsx). Folosesc demo.")
        if df.empty:
            df = pd.DataFrame([
                {"Nume":"Ana Ionescu","Email":"ana@kuziini.ro","Secție":"Proiectare","Responsabil":1,"Rol":"owner"},
                {"Nume":"Mihai Pop","Email":"mihai@kuziini.ro","Secție":"Producție","Responsabil":1,"Rol":"project_manager"},
                {"Nume":"Ioana Dinu","Email":"ioana@kuziini.ro","Secție":"Montaj","Responsabil":0,"Rol":"user"},
            ])

        rename = {}
        for col in df.columns:
            low = str(col).strip().lower()
            if low.startswith("nume"): rename[col] = "name"
            elif "email" in low: rename[col] = "email"
            elif "sec" in low: rename[col] = "section"
            elif "respons" in low: rename[col] = "responsible"
            elif "rol" in low: rename[col] = "role"
        df = df.rename(columns=rename)
        for need in ["name","email","section","responsible","role"]:
            if need not in df.columns:
                df[need] = "" if need not in ("responsible",) else 0
        def _to01(x):
            s = str(x).strip().lower()
            return 1 if s in ("1","01","true","x","da","y") else 0
        df["responsible"] = df["responsible"].map(_to01)
        df = df.reset_index(drop=True).reset_index().rename(columns={"index":"id"})
        df["id"] += 1
        return df[["id","name","email","section","responsible","role"]]

    # PROJECTS
    @property
    def projects(self) -> pd.DataFrame:
        if self._projects is None:
            self._projects = self._load_projects()
        return self._projects

    def _load_projects(self) -> pd.DataFrame:
        fpath, sheet = _find_excel_path("projects")
        df = pd.DataFrame()
        if fpath:
            try:
                df = pd.read_excel(fpath, sheet_name=sheet, engine="openpyxl")
                self._note(f"Loaded {os.path.basename(fpath)} (sheet: {sheet}) — {df.shape[0]} rânduri.")
            except Exception as e:
                self._note(f"Eroare citire {os.path.basename(fpath)}: {e!r}. Folosesc demo.")
        else:
            self._note("Nu am găsit fișierul de proiecte în /data (ex: proiecte.xlsx). Folosesc demo.")

        if df.empty:
            today = date.today()
            df = pd.DataFrame([{
                "Proiect":"Magazin Avestor", "Companie":"Avestor SRL", "Persoană de contact":"Maria Ionescu", "Email":"maria@client.ro",
                "Etaj":0, "Valoare":50000, "Tranșa1":50, "Tranșa2":25, "Tranșa3":20, "Tranșa4":5,
                "Dispunere pe secții":"Proiectare, Producție, Montaj", "Progres secții":"Proiectare=80; Producție=40; Montaj=0",
                "Start": today, "Final": today, "Status":"in_progress"
            }])

        # normalize header
        rename = {}
        for col in df.columns:
            low = str(col).lower()
            sec_keys = ("secț", "secti", "sectie", "sectii", "sect")
            def has_sec_kw(s: str) -> bool: return any(k in s for k in sec_keys)

            if low.startswith("proiect"): rename[col] = "name"
            elif "compan" in low: rename[col] = "company"
            elif "persoan" in low: rename[col] = "contact_name"
            elif "email" in low: rename[col] = "contact_email"
            elif "etaj" in low: rename[col] = "floor"
            elif "valoare" in low: rename[col] = "value"
            elif ("dispunere" in low) or (has_sec_kw(low) and "prog" not in low): rename[col] = "sections_raw"
            elif ("progres" in low) and has_sec_kw(low): rename[col] = "sections_progress_raw"
            elif re.search(r"(tran[șs]?a|transa)\s*1|(^|[^0-9])50($|[^0-9])", low): rename[col] = "inst1"
            elif re.search(r"(tran[șs]?a|transa)\s*2|(^|[^0-9])25($|[^0-9])", low): rename[col] = "inst2"
            elif re.search(r"(tran[șs]?a|transa)\s*3|(^|[^0-9])20($|[^0-9])", low): rename[col] = "inst3"
            elif re.search(r"(tran[șs]?a|transa)\s*4|(^|[^0-9])5($|[^0-9])",  low): rename[col] = "inst4"
            elif low.startswith("start") or "data start" in low: rename[col] = "start"
            elif "final" in low or "dead" in low or "sfâr" in low or "sfars" in low: rename[col] = "end"
            elif "status" in low: rename[col] = "status"
        df = df.rename(columns=rename)

        # ensure required
        for need in ["name","company","contact_name","contact_email","floor","value","inst1","inst2","inst3","inst4","sections_raw","sections_progress_raw"]:
            if need not in df.columns:
                df[need] = None

        # value & installments
        df["value"] = df["value"].map(_parse_money)
        for k in ["inst1","inst2","inst3","inst4"]:
            df[k] = df[k].map(_parse_pct)

        # sections list + progress mapping
        sec_names, sec_prog = [], []
        for _, r in df.iterrows():
            names = _split_list(r.get("sections_raw",""))
            prog_raw = r.get("sections_progress_raw","")
            pmap = _parse_kv_list(prog_raw)
            if not pmap and isinstance(prog_raw, str):
                nums = [p for p in re.split(r"[;,/|]+", prog_raw) if p.strip()]
                vals = [_parse_pct(n) for n in nums]
                if names and vals and len([v for v in vals if v is not None]) == len(names):
                    pmap = {n:v for n,v in zip(names, vals)}
            sec_names.append(names)
            sec_prog.append(pmap)
        df["sections"] = sec_names
        df["sections_progress"] = sec_prog

        # amounts per instalment
        def _amount(pct, total):
            try:
                if pct is None or total is None: return None
                return round(float(total) * float(pct) / 100.0, 2)
            except Exception: return None
        df["inst1_amount"] = df.apply(lambda r: _amount(r["inst1"], r["value"]), axis=1)
        df["inst2_amount"] = df.apply(lambda r: _amount(r["inst2"], r["value"]), axis=1)
        df["inst3_amount"] = df.apply(lambda r: _amount(r["inst3"], r["value"]), axis=1)
        df["inst4_amount"] = df.apply(lambda r: _amount(r["inst4"], r["value"]), axis=1)

        # overall progress
        def _overall(pmap: Dict[str, float]) -> Optional[float]:
            vals = list((pmap or {}).values())
            return round(sum(vals)/len(vals), 1) if vals else None
        df["progress_overall"] = df["sections_progress"].apply(_overall)

        # dates
        if "start" in df.columns:
            df["start"] = pd.to_datetime(df["start"], errors="coerce", dayfirst=True).dt.date
        else:
            df["start"] = None
        if "end" in df.columns:
            df["end"] = pd.to_datetime(df["end"], errors="coerce", dayfirst=True).dt.date
        else:
            df["end"] = None
        if "status" not in df.columns:
            df["status"] = None

        df = df.reset_index(drop=True).reset_index().rename(columns={"index":"id"})
        df["id"] += 100

        cols = ["id","name","company","contact_name","contact_email","floor","value",
                "inst1","inst2","inst3","inst4","inst1_amount","inst2_amount","inst3_amount","inst4_amount",
                "sections","sections_progress","progress_overall","start","end","status"]
        return df[cols]

    def get_responsibles_by_section(self) -> Dict[str, list]:
        df = self.users
        d: Dict[str, list] = {}
        for _, r in df.iterrows():
            if r["responsible"] == 1:
                d.setdefault(r["section"], []).append(r["name"])
        return d

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "notes": self.last_notes,
            "users_rows": int(self.users.shape[0]),
            "projects_rows": int(self.projects.shape[0]),
            "users_columns": list(self.users.columns),
            "projects_columns": list(self.projects.columns),
        }

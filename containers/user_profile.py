# containers/user_profile.py
from __future__ import annotations

import base64, re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from utils.data_loader import data, PROJECTS_XLSX

APP_ROOT = Path(__file__).resolve().parents[1]
AVATAR_DIR = APP_ROOT / "assets" / "avatars"
ATTACH_DIR = APP_ROOT / "attachments"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
ATTACH_DIR.mkdir(parents=True, exist_ok=True)

# ---------- helpers ----------
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")

def _avatar_path(email: str, name: str) -> Path:
    if email:
        return AVATAR_DIR / f"{_slug(email)}.png"
    return AVATAR_DIR / f"{_slug(name)}.png"

def _proj_sections_and_progress(row: pd.Series) -> Tuple[List[str], List[int]]:
    secs = [s.strip() for s in str(row.get("sections", "")).split(",") if s.strip()]
    prog_raw = [p.strip() for p in str(row.get("sections_progress", "")).split(",") if str(row.get("sections_progress", "")).strip()]
    prog = []
    for p in prog_raw:
        try:
            prog.append(int(float(p)))
        except Exception:
            prog.append(0)
    if len(prog) < len(secs):
        prog += [0] * (len(secs) - len(prog))
    elif len(prog) > len(secs):
        prog = prog[: len(secs)]
    return secs, prog

def _save_files(files, proj_id: str, section: str) -> List[str]:
    saved = []
    if not files:
        return saved
    target = ATTACH_DIR / proj_id / section
    target.mkdir(parents=True, exist_ok=True)
    for f in files:
        fname = f.name.replace("/", "_").replace("\\", "_")
        with open(target / fname, "wb") as out:
            out.write(f.getbuffer())
        saved.append(str((target / fname).relative_to(APP_ROOT)))
    return saved

def _preview_upload(file):
    if not file:
        return
    name = file.name.lower()
    if any(name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
        st.image(file, caption=file.name, use_container_width=True)
    elif name.endswith(".pdf"):
        b64 = base64.b64encode(file.getvalue()).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="320" style="border:1px solid #bbb;border-radius:8px;"></iframe>',
            unsafe_allow_html=True,
        )
    else:
        st.info(f"Fișier încărcat: {file.name}")

def _user_projects(dfp: pd.DataFrame, user_name: str, user_sections: List[str]) -> pd.DataFrame:
    if dfp is None or dfp.empty:
        return pd.DataFrame()
    p = dfp.copy()
    p["participants"] = p["participants"].astype(str).fillna("")
    p["responsible"] = p["responsible"].astype(str).fillna("")
    p["sections"] = p["sections"].astype(str).fillna("")
    mask_member = (
        p["responsible"].str.fullmatch(re.escape(user_name), case=False, na=False)
        | p["participants"].str.contains(re.escape(user_name), case=False, na=False)
    )
    sec_mask = False
    for s in user_sections:
        sec_mask = sec_mask | p["sections"].str.contains(re.escape(s), case=False, na=False)
    return p[mask_member | sec_mask].copy()

def _extract_delivered_on(notes: str) -> date | None:
    if not notes:
        return None
    m = re.search(r"DELIVERED_ON:\s*(\d{4}-\d{2}-\d{2})", str(notes))
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except Exception:
            return None
    return None

def _classify_deliveries_for_user(df: pd.DataFrame) -> Dict[str, int]:
    if df.empty:
        return {"ontime": 0, "delay_2_3": 0, "critical": 0, "delivered": 0}
    d = df.copy()
    d["delivered_on"] = d["notes"].apply(_extract_delivered_on)
    d = d[~d["delivered_on"].isna()].copy()
    if d.empty:
        return {"ontime": 0, "delay_2_3": 0, "critical": 0, "delivered": 0}
    d["end"] = pd.to_datetime(d["end"], errors="coerce").dt.date
    d["delay"] = (d["delivered_on"] - d["end"]).apply(lambda x: x.days if isinstance(x, timedelta) else np.nan)
    ontime = int((d["delay"] <= 0).sum())
    delay_2_3 = int(((d["delay"] >= 2) & (d["delay"] <= 3)).sum())
    critical = int((d["delay"] > 3).sum())
    return {"ontime": ontime, "delay_2_3": delay_2_3, "critical": critical, "delivered": len(d)}

def _update_section_status(proj_id: str, section: str, new_progress: int, note: str, files_saved: List[str], visible_all: bool, user_name: str) -> None:
    try:
        df = pd.read_excel(PROJECTS_XLSX, sheet_name="Proiecte", engine="openpyxl")
    except Exception:
        st.error("Nu pot deschide fișierul Proiecte.")
        return

    if df.empty or "id" not in df.columns:
        st.error("Nu găsesc proiectele în fișier.")
        return

    m = df["id"].astype(str) == str(proj_id)
    if not m.any():
        st.error("Proiectul selectat nu a fost găsit.")
        return

    i = df.index[m][0]
    secs, prog = _proj_sections_and_progress(df.loc[i])
    if section not in secs:
        st.error(f"Secția «{section}» nu există în acest proiect.")
        return

    idx = secs.index(section)
    prog[idx] = int(new_progress)
    df.at[i, "sections_progress"] = ", ".join(str(x) for x in prog)
    df.at[i, "progress_overall"] = float(round(sum(prog) / max(len(prog), 1), 1))

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    files_str = ", ".join(files_saved) if files_saved else ""
    entry = f"[UPD][{now}][USER:{user_name}][SEC:{section}][ALL:{1 if visible_all else 0}] {note.strip()} | FILES: {files_str}"
    prev_notes = str(df.at[i, "notes"]) if pd.notna(df.at[i, "notes"]) else ""
    df.at[i, "notes"] = (prev_notes + ("\n" if prev_notes else "") + entry).strip()

    with pd.ExcelWriter(PROJECTS_XLSX, engine="openpyxl", mode="w") as xlw:
        df.to_excel(xlw, sheet_name="Proiecte", index=False)

def _mark_project_delivered(proj_id: str) -> None:
    try:
        df = pd.read_excel(PROJECTS_XLSX, sheet_name="Proiecte", engine="openpyxl")
    except Exception:
        st.error("Nu pot deschide fișierul Proiecte.")
        return
    if df.empty or "id" not in df.columns:
        st.error("Nu găsesc proiectele în fișier.")
        return
    m = df["id"].astype(str) == str(proj_id)
    if not m.any():
        st.error("Proiectul selectat nu a fost găsit.")
        return
    i = df.index[m][0]
    df.at[i, "progress_overall"] = 100.0
    prev_notes = str(df.at[i, "notes"]) if pd.notna(df.at[i, "notes"]) else ""
    tag = f"DELIVERED_ON: {date.today().isoformat()}"
    if tag not in prev_notes:
        df.at[i, "notes"] = (prev_notes + ("\n" if prev_notes else "") + tag).strip()
    with pd.ExcelWriter(PROJECTS_XLSX, engine="openpyxl", mode="w") as xlw:
        df.to_excel(xlw, sheet_name="Proiecte", index=False)

# ---------- UI ----------
def render(ctx=None, **kwargs):
    st.caption("Profil utilizator — build nou")

    st.markdown("""
    <style>
      .kpi{border-radius:12px;padding:10px 12px;margin:4px 0;color:#111;}
      .green{background:#dcfce7;border:1px solid #86efac;}
      .amber{background:#ffedd5;border:1px solid #fdba74;}
      .red{background:#fee2e2;border:1px solid #fca5a5;}
      .gray{background:#f3f4f6;border:1px solid #e5e7eb;}
      .chip{display:inline-block;padding:4px 10px;border:1px solid #e5e7eb;border-radius:999px;margin-right:6px;margin-bottom:6px;background:#fff;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 👤 Profil utilizator")

    dfu = data.users.copy()
    dfp = data.projects.copy()

    if dfu is None or dfu.empty:
        st.warning("Nu există utilizatori încărcați.")
        return

    auth_email = st.session_state.get("auth_email") or st.session_state.get("current_user_email", "")
    user_row = None
    if auth_email and auth_email in dfu["email"].astype(str).values:
        user_row = dfu[dfu["email"].astype(str) == str(auth_email)].iloc[0]
    else:
        sel = st.selectbox("Alege utilizatorul (test)", dfu["email"].astype(str).tolist(), index=0)
        user_row = dfu[dfu["email"].astype(str) == sel].iloc[0]

    user_name = str(user_row.get("name", "")).strip()
    user_email = str(user_row.get("email", "")).strip()
    user_role = str(user_row.get("role", "")).strip()
    raw_sections = str(user_row.get("section", "")).strip()
    user_sections = [s.strip() for s in re.split(r"[;,/|]", raw_sections) if s.strip()]

    # avatar
    av_path = _avatar_path(user_email, user_name)
    colA, colB = st.columns([1, 2])
    with colA:
        if av_path.exists():
            st.image(str(av_path), caption="Avatar", use_container_width=True)
        else:
            st.markdown("_(fără avatar)_")
        up = st.file_uploader("Încarcă avatar", type=["png","jpg","jpeg","webp"], key="up_avatar")
        if up is not None:
            with open(av_path, "wb") as f:
                f.write(up.getvalue())
            st.success("Avatar actualizat. Reîncarcă pagina dacă nu se vede imediat.")

    with colB:
        st.markdown(f"### {user_name}")
        st.caption(f"{user_email} • {user_role}")
        if user_sections:
            st.markdown("Secții:")
            st.markdown("".join([f'<span class="chip">{s}</span>' for s in user_sections]), unsafe_allow_html=True)

    # KPI
    col1, col2, col3, col4 = st.columns(4)
    key_log = f"logins_{_slug(user_email or user_name)}"
    st.session_state[key_log] = st.session_state.get(key_log, 0) + 1
    with col1:
        st.markdown(f'<div class="kpi gray"><b>Autentificări</b><br><span style="font-size:1.3rem">{st.session_state[key_log]}</span></div>', unsafe_allow_html=True)

    myp = _user_projects(dfp, user_name, user_sections)
    with col2:
        st.markdown(f'<div class="kpi gray"><b>Proiecte implicare</b><br><span style="font-size:1.3rem">{myp.shape[0]}</span></div>', unsafe_allow_html=True)

    classes = _classify_deliveries_for_user(myp)
    with col3:
        st.markdown(f'<div class="kpi green"><b>Livrate în termen</b><br><span style="font-size:1.3rem">{classes["ontime"]}</span></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi amber"><b>Întârziere 2–3 zile</b><br><span style="font-size:1.3rem">{classes["delay_2_3"]}</span></div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        st.markdown(f'<div class="kpi red"><b>Risc critic (&gt;3 zile)</b><br><span style="font-size:1.3rem">{classes["critical"]}</span></div>', unsafe_allow_html=True)
    if not myp.empty:
        tmp = myp.copy()
        tmp["end"] = pd.to_datetime(tmp["end"], errors="coerce").dt.date
        today = date.today()
        overdue_active = int(((tmp["end"] < today) & (tmp.get("progress_overall", 0) < 100)).sum())
    else:
        overdue_active = 0
    with c6:
        st.markdown(f'<div class="kpi gray"><b>Depășite (active)</b><br><span style="font-size:1.3rem">{overdue_active}</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Lista proiectelor mele
    st.markdown("### 📂 Proiectele mele")
    if myp.empty:
        st.info("Nu ai proiecte asociate momentan.")
        return

    show_cols = ["id", "name", "company", "start", "end", "progress_overall", "sections"]
    for c in show_cols:
        if c not in myp.columns:
            myp[c] = None
    st.dataframe(myp[show_cols].sort_values(by="end", ascending=True), use_container_width=True, height=250)

    options = myp["id"].astype(str).tolist()
    proj_id = st.selectbox("Selectează proiect", options, index=0)
    p_row = myp[myp["id"].astype(str) == proj_id].iloc[0]
    proj_name = str(p_row.get("name", ""))
    secs, prog = _proj_sections_and_progress(p_row)

    intersect_secs = [s for s in secs if s in user_sections]
    if not intersect_secs:
        st.warning("Proiectul selectat nu include secțiile tale.")
        return

    st.markdown(f"### 🏭 {proj_id} — {proj_name}")
    cols = st.columns(min(3, len(intersect_secs)))
    for idx, sec in enumerate(intersect_secs):
        with cols[idx % len(cols)]:
            st.markdown(f"#### {sec}")
            current_prog = prog[secs.index(sec)] if sec in secs else 0
            new_prog = st.slider(f"Progres {sec}", 0, 100, current_prog, key=f"up_prog_{proj_id}_{sec}")
            note = st.text_area(f"Adnotare ({sec})", key=f"up_note_{proj_id}_{sec}", height=90, placeholder="Observații pentru această secție…")
            files = st.file_uploader(f"Documente ({sec})", type=["png","jpg","jpeg","webp","pdf"], accept_multiple_files=True, key=f"up_files_{proj_id}_{sec}")
            vis_all = st.checkbox("Vizibil pentru toate secțiile", value=False, key=f"up_all_{proj_id}_{sec}")
            if files:
                for f in files: _preview_upload(f)
            if st.button(f"💾 Salvează {sec}", key=f"save_{proj_id}_{sec}"):
                saved = _save_files(files, proj_id, sec)
                _update_section_status(proj_id, sec, new_prog, note, saved, vis_all, user_name)
                st.success("Actualizat.")
                st.experimental_rerun()

    st.markdown("---")

    cdl, csp = st.columns([1, 2])
    with cdl:
        if st.button("✅ Marchează proiect livrat (100%))"):
            _mark_project_delivered(proj_id)
            st.success("Proiect marcat ca livrat. KPI-urile se vor actualiza.")
            st.experimental_rerun()

    st.markdown("### 📎 Atașamente proiect")
    att_dir = ATTACH_DIR / proj_id
    listed = False
    if att_dir.exists():
        st.caption("Fișiere (listare din sistemul de fișiere proiect):")
        for sub in sorted(att_dir.glob("**/*")):
            if sub.is_file() and sub.suffix.lower() in (".png",".jpg",".jpeg",".webp",".pdf"):
                listed = True
                if sub.suffix.lower() == ".pdf":
                    try:
                        with open(sub, "rb") as fh:
                            b64 = base64.b64encode(fh.read()).decode("utf-8")
                        st.markdown(
                            f'<div style="border:1px solid #e5e7eb;border-radius:8px;margin:4px 0;"><div style="padding:6px 8px;background:#f9fafb;">{sub.name}</div><iframe src="data:application/pdf;base64,{b64}" width="100%" height="280" style="border:0;"></iframe></div>',
                            unsafe_allow_html=True,
                        )
                    except Exception:
                        st.write(sub.name)
                else:
                    st.image(str(sub), caption=sub.name, use_container_width=True)
    if not listed:
        st.caption("_Nu sunt atașamente salvate încă._")
